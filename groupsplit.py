import argparse
from multiprocessing.sharedctypes import Value
import pandas as pd
import splitwise
from splitwise import Splitwise,Group, User, CurrentUser, Expense
from splitwise.user import ExpenseUser
from typing import List
import os
import json
import webbrowser
import app
import numpy as np
import multiprocessing
def match_name(name:str, user:User):
    """Matches a name to a user, based on firstname.lastname string"

    Args:
        name (str): Name to match, in format 'firstname.lastname' or 'firstname'
        user (User): User to match to.

    Returns:
        bool: If the user is matched
    """
    try:
        firstname, lastname = name.split('.')
    except ValueError:
        firstname = name.split('.')[0]
        lastname = None
    if user.first_name.lower() == firstname.lower():
        if lastname is None or user.last_name.lower() == lastname.lower():
            return True
    return False
def make_default_split(split_string:str,members:List[User]):
    """Makes a list of splits from a splitstring

    Args:
        split_string (str): the string from args

    Raises:
        ValueError: If a value cannot be split

    Returns:
        list: list of 2-tuples of form (name,amount)
    """
    if split_string is None:
        return [(member,1./len(members)) for member in members]
    splits = split_string.split(',')

    ret = []
    
    for s in splits:
        try:
            person, amount = s.split('=')
        except ValueError:
            raise ValueError(f'Did not supply correct splitstring: cannot split {s}')
        matched_member = None
        for member in members:
            if match_name(person,member):
                matched_member = member
                break
        ret.append((matched_member,float(amount)))
       
    return ret

def match_group(client:Splitwise, groupname:str):
    """Matches a groupname to a Splitwise client's groups, based on auth.

    Args:
        client (Splitwise): Splitwise client
        groupname (str): Group name

    Returns:
        Group: matched group
    """
    groups = client.getGroups()
    matched_group = None
    for group in groups:
        if group.name == groupname:
            matched_group = group
            break
    return matched_group
def match_user(user, group:Group):
    """Based on a username, returns their member object within a group

    Args:
        user (str): User's name, in firstname.lastname format
        group (Group): Group to match in

    Raises:
        ValueError: If the user is not in the group

    Returns:
        User: User object
    """     
    for member in group.members:
        if match_name(user, member):
            return member
    raise ValueError(f"Unable to match user argument {user} to members in group")
def make_transaction(args, row):
    """Returns the properties of the transacion

    Args:
        args (Namespace): Arguments
        row (pd.Series): The row

    Returns:
        tuple: date,description, amount
    """
    date = row[args.date_col]
    desc = row[args.desc_col]
    amount = row[args.amount_col]
    return date, desc, amount
def get_name(user:User):
    fn = user.first_name
    ln = user.last_name
    if ln is None:
        return fn
    return f"{fn} {ln}"
def write_creds(creds, id_file):
    os.makedirs(os.path.dirname(id_file), exist_ok=True)
    with open(id_file,'w') as fp:
        json.dump(creds, fp)
def main(args):
    
    fn = args.file
    groupname = args.group
    id_file = args.identity_file
    dry_run = args.dry_run
    default_split = args.default_split
    with open(fn,'r') as fp:
        transactions_df = pd.read_csv(fn, usecols=[args.date_col, args.desc_col, args.amount_col])
    
    if os.path.isfile(id_file):
        with open(id_file,'r') as fp:
            creds = json.load(fp)
    else:
        # Need to make file at location
        print('Auth file not found, please enter creds now')
        consumer_key = input('Consumer key: ')
        consumer_secret = input('Consumer secret: ')
        creds = {}
        creds['consumer_key'] = consumer_key
        creds['consumer_secret'] = consumer_secret
        write_creds(creds, id_file)
    client = splitwise.Splitwise(**creds)
    if "access_token" not in creds:
        queue = multiprocessing.Queue()
    
        flask_process = multiprocessing.Process(target=app.start_server, args=(queue,))
        flask_process.start()
        url, secret = client.getAuthorizeURL()
        webbrowser.open(url)
        try:
            d = queue.get(True, timeout=30)
        except:
            raise RuntimeError('Unable to get auth from Splitwise')
        flask_process.terminate()
        access_token = client.getAccessToken(oauth_token_secret=secret,**d)
        creds['access_token'] = access_token
        write_creds(creds, id_file)
    else:
        access_token = creds['access_token']
    client.setAccessToken(access_token=access_token)
    group = match_group(client, groupname)
    if args.user is None:
        current_user = client.getCurrentUser()
    else:
        current_user = match_user(args.user, group)

    splits = make_default_split(default_split,group.getMembers())
    
    transactions_df = transactions_df.dropna(axis=0,how='all')
    transactions_df[args.date_col] = pd.to_datetime(transactions_df[args.date_col])
    transactions_df[args.amount_col] = -transactions_df[args.amount_col].astype(float)
    # print(transactions_df)
    # TODO category matching
    # for category in client.getCategories():
    #     print(category.name)
    #     print("_"*10)
    #     for subcategory in category.getSubcategories():
    #         print(subcategory.name)
    expenses = []
    for i,row in transactions_df.iterrows():
        date, desc, amount = make_transaction(args, row)
        amount = float(amount)
        total_amount = 0
        expense = Expense()
        expense.setCost(str(amount))
        expense.setDescription(desc)
        
        expense.setDate(date)
        expense.setGroupId(group.getId())
        expense_users = []
        for j,(member,splitamount) in enumerate(splits):
            true_amount = np.round(amount*splitamount,2)
            total_amount += true_amount
            if j+1 == len(splits):
                if not np.isclose(total_amount,amount):
                    print(f"Total amount of split {total_amount} does not equal transaction amount {amount}, adding the difference to {get_name(member)}'s share")
                    true_amount += (amount-total_amount)
            transactions_df.loc[i,get_name(member)] = true_amount
            expense_user = ExpenseUser()
            expense_user.setId(member.getId())
            if current_user.getId() == member.getId():
                # This user posted, therefore paid for it
                expense_user.setPaidShare(str(amount))
                expense_user.setOwedShare(str(true_amount))
            else:
                expense_user.setPaidShare("0.00")
                expense_user.setOwedShare(str(true_amount))
            
            expense_users.append(expense_user)
        expense.setUsers(expense_users)
        expenses.append(expense)
    print(transactions_df)
    if not dry_run:
        if input("Does the following transaction list look correct? (y/n)").lower() == 'y':
            for expense in expenses:
                expense, errors = client.createExpense(expense)
                if errors:
                    raise ValueError(f'Errors: {errors.getErrors()}')
            
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    default_id_filedir = os.path.join(os.path.expanduser('~'),'.splitwise','secret.json')
    parser.add_argument('file', help='The file to parse')
    parser.add_argument('group', help='The group to post the transactions to')
    parser.add_argument('--dry-run', help='Dry run and just print proposed output', action='store_true')
    parser.add_argument('-i','--identity-file',help='Auth file', default=default_id_filedir)
    parser.add_argument('--date-col',help='The header of the column containing the date', default='Transaction Date')
    parser.add_argument('--desc-col',help='The header of the column containing the description', default='Description')
    parser.add_argument('--amount-col',help='The header of the column containing the amount', default='Amount')
    parser.add_argument('--default-split',help='A comma-delimited, kwarg-style default split, in fractional costs. I.e --default-split="bob=0.8,alice.smith=0.1,alice.johnson=0.1" would split between Bob and the two Alices unequally', default=None)
    parser.add_argument('--user','-u',help='Post transactions as user', default=None)
    args = parser.parse_args()

    main(args)