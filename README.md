# confluence-to-degreed

# Description

This repo creates an AWS Step Function that integrates specified content (via a white list of space keys) from a confluence wiki site to a Degreed LXP instance. 
# Process Sequence Diagram

![Sequence Diagram](./images/sequence.svg?sanitize=true)

# Process Activity Diagram

![Activity Diagram](https://s7v9l3nxx5.execute-api.us-west-2.amazonaws.com/plantuml/png/nLR1RXit4BtpAmZv4CUGvTXf3WrY0uuTjmPIm8YDzb040hKxAx7YaWkIAqKe-kzzG-xAMbL9WrvwI20lPuOpxysROLXgsoYlQcbTfFUgMCwzQsrvuuppib0bnPbfIOIXdVCb-MmpCt0wUFwqqCNIKWZorSxvTH7rIiVD_bt1g4XpJvj3jj-uRsZpRtTsGOvA-h5uLHumkNCsPflrGaSIGXoVl9IdfrToT6DSMwvLB1RoITTKoWyhid4ayg6p5O2o1Sdev2rN0el7I8syQos2EvijBoyl7yxnds2WODjiatbNyBrlZzweLsL9Lm_8onWoyiCNAbeEaCAzEqjcLu9icS3Ezt_K8Jusgg0mof4DLL5yekWrhIZ8k23v6rTaO2Whr9UjXKAOKQD2W2TRrN86WBa8TWcuKLHT0Sbj0GTNLRq1_sd8X-TqjbLUV4-LlwWcetGAq2hLchWjSCzoEYsSBLhl0VBcylLqUXY9trDTykZyinobdp_d3AVd7J0p5wEhnGS57aEoxMgGVeiMRehWbWiMSQ5YDXnB1gi2iK7gABK51Wf7LEXAW-sRnrzbfGrb5w1ZvPnYa0hfbmoOibBnPoLltuzbuKb5RUTiAKvEHckzrDEGEJmvaL7D34taFLzKcBP4Mg-bqNOP4W-4_4MZvlHM7CbQQIjRR_2JFztVNl9VALzymYKRFXpWn0ozPePwgdR1kzW7xs9qqExFoMJorxuj6btiUmzkt3SV70hHAoIhxjgO1vJKjxNNyqKK7vq336sJMj2szGpikIhL3cgiuCzkHImWoR2YZvtl-2kXSu0fUWR_SBE0dW-W22sE4DegxdQH1aCOPoApGl3R1SekqObT0J2_VGDD3gZXX_z73JzvXLpFeVaPJwxFMq1tPD6d9tSyBX3bAnuNXpriN7pDmnwGtj1aHtigHs4-qRHvG7s7vex1TUB_x5toFxgQ567rKcwrA8PQPEwsOfGgz2ha65DjURGxlzaASOVHVG3be7_tmVhcgHsUxhL-jqKwuu407bfZK0pQknzL6000XxnL-AQYCcu-PcJmYKensyXM0qvv33kuL2-J5fes7eHL0Be4gpmkSn9doaTT60e9rJ7Zc4PN0b9S9o2tE4hWsFbDUx-TaOOb7J2oDi9IvcA6HTCOv67qabA09Df2SP58cBzKRMmXOJ5hy_goRZtcr0DHdSHNEcHigRS_VoDhRLiGPbGzAnMcO4skZRlQ708Cp9-PE4qCF7Y7QHm-KO0Kmx2BkxDkj_fiWiGXWvIlCyQj6IFVedoAFATl5eJTohHnQ_UfTb3rj4arnpWFgMlbi1s5b1b430XTWJ4-ba2p9Awz_4h4iMJKIaV1leWSGpKDATzR3-_85un1a5yom0nsIORIJFml9UpijMt-s6iLWhz80G3eGZQ63SPfR7iCwEJQDVVzRNSF---40-e5ddtFe3lmNtbN7mQ1jo42j4sf8dMi3VrhYWg7wZd8xcqvSmwHEdYK0-7PfFf0QTZKh53iXHLQXR0wTDqu7v78Igk-Y5PBmAhGJmiClveAh14Twd7Qv17_k75OptEFHwbKXNTuqpOOM6kr2HFmS6qtSP5V3ofkUVX7kZcbXMBcmHgU7EKcfSLP50ms4jkPZ10mlrBAyYnN9yGJf9sKjjOWVKuMQpKEwEagJ0CZxzZ6WNkuTEFXyUxfGGOyFYT2t66z6hFPYUZoYpFjPkupIjs5ySzNzFSzJ_em5esdfk7QkJVJ4u2-HEZCFelxRm00)

# Configuration

Configuration is handled through the SSM parameter store. The Cloud Formation Template takes a "SSMPathRoot" Parameter that is the top level of the parameter hierarchy - in the diagram below, it corresponds with the "confluence-to-degreed" node. 

<insert mindmap here>

## Config Options

### slack container

#### slack_token

A SecureString (encoded with the key created by the cloud formation template) with the token to provide to the slacke API.

#### slack_channel

A String representing the channel to be posting events/errors to.

### wiki container

#### url

A String representing the URL head for the wiki api. Since URL's can't be natively stored in params, replace the "http" protocol name with "urlhead", and "https" with "urlheads" - the code will substitute accordingly. Do NOT include any URI beyond the root (as the URI's are handled in the code). Example urlheads://wiki.somewhere.com/

#### uiurl

A String representing the URL head for the wiki UI (the web root). Since URL's can't be natively stored in params, replace the "http" protocol name with "urlhead", and "https" with "urlheads" - the code will substitute accordingly. Do NOT include any URI beyond the root (as the URI's are handled in the code). Example urlheads://wiki.somewhere.com/

#### passwd

A SecureString (encoded with the key created by the cloud formation template) containing the password for the wiki API (using basic auth, combined with the username parameter). 

#### username

A String containing the username to authenticate with against the API. 

#### item_limit

A String containing the number of items to set as the limit parameter for API pagination. This should be set at or near the maximum number of pages the API can request without expansion (in my instance of Confluence, that's 500). Setting higher than the limit will create gaps in the "all_pages" inventory, which could lead to links being removed from Degreed.

#### max_labels

A String defining the maximum number of labels to push through to degreed as "skill tags". The code will take the first n (where n is the max_labels value).

#### spaces

A StringList (a string listing items, separated by commas) containing all of the "whitelisted" Space Keys.

### degreed container

#### client_id

A SecureString (encoded with the key created by the cloud formation template) containing the client_id for authentication against the degreed API - you'll need to get this from your degreed account team.

#### client_secret

A SecureString (encoded with the key created by the cloud formation template) containing the client_secret for authentication against the degreed API - you'll need to get this from your degreed account team.

#### oauthurl

A String containing the url (with http replaced with "urlhead") for the oauth token endpoint for the degreed API. 

#### url

A String containing the url (with http replaced with "urlhead") for the API endpoints - do not include any URI - just the protocol + host, like urlheads://api.degreed.com/

#### article_limit

A String containing the number to use for the "limit" parameter for degreed API. This should be the max available for the API, preferably, to minimize impact of paging on time. 

### dynamo_table (optional)

The dynamo_table container provides the user the option to store the spac e key whitelist in a dynamo db table (each record contains a single "space" attribute including the space key to be whitelisted). The default is to use the wiki/spaces parameter to contain the whitelist.

#### arn

A String containing the arn to the table.

#### name

A String containing the name of the table. 
