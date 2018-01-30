#!/usr/bin/env python3
"""
A small AWS Multi Factor Authentication tool to create a session token
for an assumed role and updates the AWS credentials file for Terraform.
"""

import argparse
from sys import stderr, exit as sysexit
from os import path
from shutil import copyfile
from uuid import uuid4
from boto3 import client
from botocore.exceptions import ClientError, NoCredentialsError, ParamValidationError

ARGPARSER = argparse.ArgumentParser(
    description='Generates a Session Token using a Role and MFA Device'
    )
ARGPARSER.add_argument(
    "-d",
    type=int,
    default="3600",
    metavar="3600",
    help="duration the token is valid (sec)",
    required=False
    )
ARGPARSER.add_argument(
    "-p",
    type=str,
    default="terraform_session",
    metavar="terraform_session",
    help="profile name for the Session Token",
    required=False
    )
ARGPARSER.add_argument(
    "-v",
    action='store_false',
    help="disables SSL Verification",
    required=False
    )
ARGS = ARGPARSER.parse_args()
AWS_DEFAULT_ROLE = "TerraformRole"
AWS_CREDENTIALS_FILE = path.expanduser("~/.aws/credentials")
AWS_CREDENTIALS_PROFILE = "[%s]" % ARGS.p

def get_mfa_serial():
    """
    Collects the MFA Serial Number of the IAM User Account

    :return: ARN of the MFA device
    """
    try:
        global ARGS
        iam_client = client('iam', verify=ARGS.v)
        user_name = iam_client.get_user()['User']['UserName']
        serial = iam_client.list_mfa_devices(
            UserName=user_name,
            MaxItems=1
            )["MFADevices"][0]["SerialNumber"]
    except ClientError as err:
        print("\nError: %s, Exiting" % err.response, file=stderr)
        sysexit(1)
    except NoCredentialsError as err:
        print("\nError: %s, Exiting" % err, file=stderr)
        sysexit(1)
    return serial

def get_session_token(role, code):
    """
    Collects the Session Token from STS using the Terraform Role and MFA Code.

    :type role: string
    :param role: Name of the Role to be Assumed in the form of ARN

    :type code: integer
    :param code: 6 digit code from the MFA device

    :return: Token details
    """
    try:
        global ARGS
        iam_client = client('iam', verify=ARGS.v)
        sts_client = client('sts', verify=ARGS.v)
        role_arn = iam_client.get_role(RoleName=role)["Role"]["Arn"]
        serial = get_mfa_serial()
        session_id = str(uuid4())
        token = sts_client.assume_role(
            DurationSeconds=ARGS.d,
            RoleSessionName=session_id,
            RoleArn=role_arn,
            SerialNumber=serial,
            TokenCode=code
            )
    except ClientError as err:
        print("\nError: %s, Exiting" % err, file=stderr)
        sysexit(1)
    except ParamValidationError as err:
        print("\nError: %s, Exiting" % err, file=stderr)
        sysexit(1)
    return token

def write_token(file, profile, token):
    """
    Creates a backup and Updates the Credentials file with a session token from STS

    :type file: string
    :param file: Credentials file name to be used

    :type profile: string
    :param profile: Title of the profile to be created or updated

    :type token: string
    :param token: The Session Token details
    """
    file_backup = file + ".bak"
    copyfile(file, file_backup)
    with open(file, "w") as out_file, open(file_backup, "r") as in_file:
        data_list = in_file.read().splitlines()
        access_key = "aws_access_key_id = " + token['Credentials']['AccessKeyId']
        secret_key = "aws_secret_access_key = " + token['Credentials']['SecretAccessKey']
        session_token = "aws_session_token = " + token['Credentials']['SessionToken']
        if profile in data_list:
            print("\nUpdating the profile %s in the credentials file" % profile)
            profile_section = data_list.index(profile)
            data_list[profile_section + 1] = access_key
            data_list[profile_section + 2] = secret_key
            data_list[profile_section + 3] = session_token
        else:
            print("\nAdding the profile %s to the credentials file" % profile)
            data_list.append("")
            data_list.append(profile)
            data_list.append(access_key)
            data_list.append(secret_key)
            data_list.append(session_token)
            data_list.append("")
        out_file.write("\n".join(data_list))

def main():
    """
    Prompts for a series of details required to generate a session token
    """
    try:
        print("\nTerraform Session Token\nHit Enter on Role for Default\n")
        entered_role = input("Role[%s]: " % AWS_DEFAULT_ROLE)
        selected_role = entered_role if entered_role else AWS_DEFAULT_ROLE
        mfa_code = input("Code: ")
        session_token = get_session_token(selected_role, mfa_code)
        write_token(AWS_CREDENTIALS_FILE, AWS_CREDENTIALS_PROFILE, session_token)
        print("Completed.")
    except KeyboardInterrupt:
        print("\nKeyboard Interrupted, Exiting")
        sysexit(0)

if __name__ == "__main__":
    main()
