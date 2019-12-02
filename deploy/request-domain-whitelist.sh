#!/bin/bash

while true
do
    read -p "Please enter you Autodesk email address: " EMAIL_ADDRESS
    echo
    if [[ "$EMAIL_ADDRESS" =~ ^[a-zA-Z0-9._%+-]+@autodesk.com ]]
    then
        break
    else
        echo "$EMAIL_ADDRESS is not a valid Autodesk email address."
    fi
done

aws support --region us-east-1 \
create-case \
--service-code amazon-acm-service \
--severity-code low \
--category-code domain-whitelisting \
--cc-email-addresses $EMAIL_ADDRESS \
--subject "Whitelist .autodesk.com for ACM. This is an Autodesk owned account." \
--communication-body "Please whitelist the .autodesk.com domain in this account. Thank you."