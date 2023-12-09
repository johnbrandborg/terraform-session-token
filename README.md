:exclamation: This repository has been archived. I recommend using command line sign-in instead.
https://docs.aws.amazon.com/signin/latest/userguide/command-line-sign-in.html

Terraform Session Token (MFA)
=================

A small AWS Multi Factor Authentication tool to create a session token for an assumed role and updates the AWS credentials file for Terraform.

Why?
----

The standard version of Terraform currently has no means of MFA support with AWS.  Terraform on execution will attempt a number way to find AWS API keys. Unfortunately when you define a profile for AWS CLI MFA in the credentials file, no keys are actually defined so Terraform can't use this setup.  Terraform Session Token allows access keys to have least priviledge access, and Terraform is able to perform it's duties safely with MFA.

Getting Started
---------------

Using 'terraform-session-token.py' the default profile is used only for assuming an elevated access role, which has a condition that MFA must be supplied. Once Authenticated session token details are placed into the credentials for use by Terraform that are valid for an hour, however this can be increased or decreased.

### Prequisities

What things you will need to install and configure

 - [Python3](https://www.python.org/)
 - [PIP3](https://pip.pypa.io)
 - [AWS CLI](https://aws.amazon.com/cli/)
 - [Python AWS-SDK (Boto3)](https://github.com/boto/boto3)
 - [Terraform](https://www.terraform.io/)

### Installation

Clone the repository or download the 'terraform-session-token.py' onto your system.

    git clone https://github.com/johnbrandborg/terraform-session-token.git

### Usage

terraform-session-token will prompt for details to be entered and update the AWS CLI credential files with a profile that Terraform is able to use.

    Terraform Session Token
    Hit Enter on Role for Default

    Role[TerraformRole]: myCustomRole
    Code: 121314

    Updating the profile [terraform_session] in the credentials file

There are some arguments you can use when running terraform-session-token, which can be viewed by parsing the '-h' or '--help' parameter.  Be aware that disabling SSL Verification if you have a 'MITM Proxy' is not recommended, and will warn about its usage.  It is better to use the CA Bundle instead, but this can be complicated.

    usage: terraform-session-token.py [-h] [-d 3600] [-p terraform_session] [-v]

    Generates a Session Token using a Role and MFA Device

    optional arguments:
      -h, --help            show this help message and exit
      -d 3600               duration the token is valid (sec)
      -p terraform_session  profile name for the Session Token
      -v                    disables SSL Verification

Once you have authenticated you should have new profile listed within the AWS Crendentials file generally located under your home directory. This can then be called upon within Terraform's AWS Provider with 'profile'.

    [terraform_session]
    aws_access_key_id = AQIEIGHLPWAHLYFCDICA
    aws_secret_access_key = VkFbHUsHvZ6HAT29w2seWdVzLUCQ/egg7A
    aws_session_token = FQoDYXdzEOv\\\\\\\wEaDJZOEU69XfSIMDva3CLnASu3rGJvN8yW3oEbbhPwLiUb6AtqeILq3BmZR1Qr6bze8xlcwKdLZAoStT4drIlhuH7vQl1EaIDXT/AAeopW9siFupGnes+jTJXLMKmfslkngdlsndgVZWalDkRiH6Bg9ZgdkMXX34AV6Ro7MDpOwRVsRe+8/OSQPdtEPDBTfrSPTyALMSDFInieiownroiFJIlwEDsrBdd379ST3Gmftav4T4E9n4R1sxrVhtPqm0tvK7Y1lfgAJgftK+W4mwceygE27Q5xFnYaVxAHfd87dFSZvQLfRt5WIOEMZMZOjVDYCjGofXMBQ==

AWS Setup
---------

Create a IAM Group with a policy to allow user accounts to assume the elevated access role.  Anyone that you want to be able to switch into the Role is added to this group.

### User Group Access Policy

Least Privileged Principles apply. The 'terraform_session' tool uses IAM to collect some details to make the AssumeRole Call to STS.

#### AWS (JSON) Example
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCollectionOfARNs",
      "Effect": "Allow",
      "Action": [
        "iam:ListMFADevices",
        "iam:GetRole",
        "iam:GetUser"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowGroupAssumeTerraformRole",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::xxxxxxxxxxxx:role/TerraformRole"
    }
  ]
}
```

#### Terraform (HCL) Example
```hcl
resource "aws_iam_policy" "assume_terraform" {
  name        = "AssumeTerraformRole"
  description = "Provides the ability to Assume the Terraform Role"
  policy      = "${data.aws_iam_policy_document.assume_terraform.json}"
}

data "aws_iam_policy_document" "assume_terraform" {
  statement {
    actions = [
      "iam:ListMFADevices",
      "iam:GetRole",
      "iam:GetUser",
    ]

    resources = ["*"]
  }

  statement {
    actions   = ["sts:AssumeRole"]
    resources = ["${aws_iam_role.terraform.arn}"]
  }
```

### Terraform Role Trust Policy

The elevated access role has a trust policy that enforces the use of MFA, and who can attempt the action.

**AWS (JSON) Example:**
```json
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

**Terraform (HCL) Example:**
```hcl
resource "aws_iam_role" "terraform" {
  name               = "TerraformRole"
  description        = "High Privileged Access for Terraform"
  assume_role_policy = "${data.aws_iam_policy_document.terraform_trust.json}"
}

data "aws_iam_policy_document" "terraform_trust" {
  statement {
    principals {
      type = "AWS"

      identifiers = [
        "arn:aws:iam::xxxxxxxxxxxx:root",
      ]
    }

    actions = ["sts:AssumeRole"]

    condition {
      test     = "Bool"
      variable = "aws:MultiFactorAuthPresent"
      values   = ["true"]
    }
  }
}
```

Terraform
---------

With a valid session_token profile Terraform Backend, Remote_State and the AWS Provider blocks can be setup to use the new profile.  If you are using S3 for backend state files ensure the Role has access to the Bucket and DynamoDB Table for state lock.

**Main.tf (HCL) Example:**
```hcl
terraform {
    required_version = ">= 0.10.2"

    backend "s3" {
        bucket         = "infrastructure-as-code"
        key            = "example/terraform.tfstate"
        region         = "us-east-1"
        encrypt        = "true"
        dynamodb_table = "terraform"
        profile        = "terraform_session"
    }
}

provider "aws" {
    region  = "us-east-1"
    profile = "terraform_session"
}
```

**Variables.tf (HCL) Example:**
```
data "terraform_remote_state" "example" {
  backend = "s3"

  config {
    bucket = "infrastructure-as-code"
    key    = "example/terraform.tfstate"
    region = "us-east-1"
    profile = "terraform_session"
  }
}
```

Authors
-------

* **John Brandborg** - *Initial work* - [Linkedin](https://www.linkedin.com/in/johnbrandborg/)

License
-------
This project is licensed under the MIT License - see the [LICENSE.md](https://github.com/johnbrandborg/terraform-session-token/blob/master/LICENSE) file for details
