# aws-session-token

A small AWS MFA authentication tool to create a session token for an assumed role and updated the AWS credentials file.

## Goal

While the AWS CLI has MFA support for assuming roles, Terraform currently has no means of MFA.  Terraform on execution will attempt a number way to find AWS API keys. Unfortunately when you define a profile for AWS CLI MFA in the credentials file, no keys are actually defined so Terraform can't use this setup.

aws-session-token will prompt for details to be entered and update the AWS CLI credential files with a profile that Terraform is able to use.

The purpose behind all of this is to have the default profile setup with least privileged access; just enough to be able to assume a role to do the real work.

The high privilege access role has a condition that MFA must be supplied.

## Getting Started

Required Software:
 - AWS CLI
 - Python3
 - AWS SDK Boto3
 - Terraform (Optional)

### Usage
    prompt$ ./aws-session-token.py

    AWS Session Token Generator
    Hit Enter on Role for Default

    Username: johnb
    Role [CloudAdmin]:
    Code: 123456


AWS Setup
---------

Create a group with a policy to allow user accounts to assume the high privilege access role.

#### User Group Access Policy (JSON)
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCollectionOfARNs",
      "Effect": "Allow",
      "Action": [
        "iam:ListMFADevices",
        "iam:GetRole"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowGroupAssumeAdminRole",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::xxxxxxxxxxxx:role/AdminRole"
    }
  ]
}
```
The high privilege access role has a trust policy that enforces the use of MFA.

#### Admin Role Trust Policy (JSON)
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAssumeRoleOnlyWithMFA",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::xxxxxxxxxxxx:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "Bool": {
          "aws:MultiFactorAuthPresent": "true"
        }
      }
    }
  ]
}
```

Terraform
---------

With a valid session_token profile Terraform Backend and AWS Provider blocks can be setup to use the new profile.

#### Main.tf Example
```
terraform {
    required_version = ">= 0.10.2"

    backend "s3" {
        bucket         = "infrastructure-as-code"
        key            = "example/terraform.tfstate"
        region         = "us-east-1"
        encrypt        = "true"
        dynamodb_table = "terraform"
        profile        = "session_token"
    }
}

provider "aws" {
    region  = "us-east-1"
    profile = "session_token"
}
```