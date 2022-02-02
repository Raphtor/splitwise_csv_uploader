# Splitwise CSV Uploader

Uploads CSVs of transactions (i.e from your bank) to Splitwise.

# Features

* Upload entire CSVs at once
* Proper Splitwise authentication using OAuth1
* Upload transactions where another person has paid
* Non-standard splits. (Want splitwise defaults, but don't want to pay for pro?)

# Installation

`pip install -r requirements.txt`

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