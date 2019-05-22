#!/usr/bin/env bash
export OS_AUTH_URL=https://c3se.cloud.snic.se:5000/v3
export OS_PROJECT_ID=ba4a690b72e14b84b6eb26adf87b30c4
export OS_PROJECT_NAME="SNIC 2018/10-51"
export OS_USER_DOMAIN_NAME="snic"
if [ -z "$OS_USER_DOMAIN_NAME" ]; then unset OS_USER_DOMAIN_NAME; fi
unset OS_TENANT_ID
unset OS_TENANT_NAME
export OS_USERNAME="s5316"
echo "Please enter your OpenStack Password for project $OS_PROJECT_NAME as user $OS_USERNAME: "
read -sr OS_PASSWORD_INPUT
export OS_PASSWORD=$OS_PASSWORD_INPUT
export OS_REGION_NAME="C3SE"
if [ -z "$OS_REGION_NAME" ]; then unset OS_REGION_NAME; fi
export OS_INTERFACE=public
export OS_IDENTITY_API_VERSION=3
