# Splitwise CSV Uploader

Uploads CSVs of transactions (i.e from your bank) to Splitwise.

# Features

* Upload entire CSVs at once
* Proper Splitwise authentication using OAuth1
* Upload transactions where another person has paid
* Non-standard splits. (Want splitwise defaults, but don't want to pay for pro?)

# Installation

Installing requirments:

`pip install -r requirements.txt`

You will need a consumer/key and secret to run this app. You can make and register an app [here](https://secure.splitwise.com/oauth_clients). When you first run this script, it will ask you for them. Alternatively, you can pass a json file with keys "consumer_key" and "consumer_secret" into the script. By default, the script will save these keys to `~/.splitwise/secret`

# Running

Basic use:

```python groupsplit.py <transactions.csv> <groupname>```

For more options, see:

```python groupsplit.py --help```


# Planned features
* Category matching
* OAuth2
* Proper CLI with PATH integration
* Add transactions without groups
* Packaging
* Tests
