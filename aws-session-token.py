#!/usr/bin/env python3

import boto3
from os import path
from shutil import copyfile
from uuid import uuid4

awsDefaultRole = "AdminRole"
awsCredentialsFile = path.expanduser("~/.aws/credentials")
awsCredentialsProfile = "[session_token]"
sessionDuration = 3600

def getMfaSerial(user):
    iam = boto3.client('iam')
    response = iam.list_mfa_devices(UserName=user,MaxItems=1)["MFADevices"][0]["SerialNumber"]
    return response

def getSessionToken(role, serial, code):
    iam = boto3.client('iam')
    sts = boto3.client('sts')
    RoleARN = iam.get_role(RoleName=role)["Role"]["Arn"]
    sessionId = str(uuid4())
    response = sts.assume_role(
        DurationSeconds=sessionDuration,
        RoleSessionName=sessionId,
        RoleArn=RoleARN,
        SerialNumber=serial,
        TokenCode=code
        )
    return response

def writeToken(file, profile, token):
    fileBackup = file + ".bak"
    copyfile(file, fileBackup)
    with open(file, "w") as outFile, open(fileBackup, "r") as inFile:
        dataList = inFile.read().splitlines()
        accessKey = "aws_access_key_id = " + token['Credentials']['AccessKeyId']
        secretKey = "aws_secret_access_key = " + token['Credentials']['SecretAccessKey']
        sessionToken = "aws_session_token = " + token['Credentials']['SessionToken']
        if profile in dataList:
            print("\nUpdating the credentials details")
            profileSection = dataList.index(profile)
            dataList[profileSection + 1] = accessKey
            dataList[profileSection + 2] = secretKey
            dataList[profileSection + 3] = sessionToken
        else:
            print("\nAdding the credentials details")
            dataList.append("")
            dataList.append(profile)
            dataList.append(accessKey)
            dataList.append(secretKey)
            dataList.append(sessionToken)
            dataList.append("")
        outFile.write("\n".join(dataList))

def main():
    print("\nAWS Session Token Generator\nHit Enter on Role for Default\n")
    userName = input('Username: ')
    mfaSerial = getMfaSerial(userName)
    enteredRole = input("Role [%s]: " % awsDefaultRole)
    selectedRole = enteredRole if enteredRole else awsDefaultRole
    mfaCode = input("Code: ")
    sessionToken = getSessionToken(selectedRole, mfaSerial, mfaCode)
    writeToken(awsCredentialsFile, awsCredentialsProfile, sessionToken)

if __name__ == "__main__":
    main()
