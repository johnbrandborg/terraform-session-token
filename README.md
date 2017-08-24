terraform-session-token
=================

A small AWS MFA authentication tool to create a session token for an assumed role and updated the AWS credentials file for Terraform.

Why?
----

Terraform itself currently has no means of MFA support.  Terraform on execution will attempt a number way to find AWS API keys. Unfortunately when you define a profile for AWS CLI MFA in the credentials file, no keys are actually defined so Terraform can't use this setup.

Using 'terraform-session-token.py' the default profile is used only for assuming the high privilege access role, which has a condition that MFA must be supplied. Once Authenticated session token details are placed into the credentials for use by Terraform.

Getting Started
---------------

### Prequisities

What things you will need to install and configure

 - [Python3](https://www.python.org/)
 - [PIP3](https://pip.pypa.io)
 - [AWS CLI](https://aws.amazon.com/cli/)
 - [Python AWS-SDK (Boto3)](https://github.com/boto/boto3)
 - [Terraform](https://www.terraform.io/)

### Installation

Clone the repository or download the 'terraform-session-token.py' onto your system.

    git clone https://github.com/johnbrandborg/terraform-session-token

### Usage

terraform-session-token will prompt for details to be entered and update the AWS CLI credential files with a profile that Terraform is able to use.

    prompt$ ./terraform-session-token.py

    Terraform Session Token
    Hit Enter on Role for Default

    Username: jsmith
    Role[AdminRole]: 'enter'
    Code: 123456

Once you have authenticated you should have new profile listed within the AWS Crendentials file located in your home directory.

    [terraform_session]
    aws_access_key_id = AQIEIGHLPWAHLYFCDICA
    aws_secret_access_key = VkFbHUsHvZ6HAT29w2seWdVzLUCQ/egg7A
    aws_session_token = FQoDYXdzEOv\\\\\\\wEaDJZOEU69XfSIMDva3CLnASu3rGJvN8yW3oEbbhPwLiUb6AtqeILq3BmZR1Qr6bze8xlcwKdLZAoStT4drIlhuH7vQl1EaIDXT/AAeopW9siFupGnes+jTJXLMKmfslkngdlsndgVZWalDkRiH6Bg9ZgdkMXX34AV6Ro7MDpOwRVsRe+8/OSQPdtEPDBTfrSPTyALMSDFInieiownroiFJIlwEDsrBdd379ST3Gmftav4T4E9n4R1sxrVhtPqm0tvK7Y1lfgAJgftK+W4mwceygE27Q5xFnYaVxAHfd87dFSZvQLfRt5WIOEMZMZOjVDYCjGofXMBQ==

AWS Setup
---------

Create a IAM Group with a policy to allow user accounts to assume the high privilege access role.  Anyone that you want to be able to switch into the Role is added to this group.

### User Group Access Policy

Least Privileged Principles apply. The 'terraform_session' tool uses IAM to collect some details to make the AssumeRole Call.

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

#### Terraform (HCL) Example
```hcl
resource "aws_iam_policy" "assume_admin" {
  name        = "AssumeAdministration"
  description = "Provides the ability to Assume the Admin Role"
  policy      = "${data.aws_iam_policy_document.assume_admin.json}"
}

data "aws_iam_policy_document" "assume_admin" {
  statement {
    actions = [
      "iam:GetRole",
      "iam:ListMFADevices",
    ]

    resources = ["*"]
  }

  statement {
    actions   = ["sts:AssumeRole"]
    resources = ["${aws_iam_role.admin.arn}"]
  }
```

### Admin Role Trust Policy

The high privilege access role has a trust policy that enforces the use of MFA.

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
resource "aws_iam_role" "admin" {
  name               = "AdminRole"
  description        = "High Privileged Access for Administrators"
  assume_role_policy = "${data.aws_iam_policy_document.admin_trust.json}"
}

data "aws_iam_policy_document" "admin_trust" {
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

With a valid session_token profile Terraform Backend and AWS Provider blocks can be setup to use the new profile.  If you are using S3 for backend state files ensure the Role has access to the Bucket and DynamoDB Table for state lock.

**Terraform (HCL) Example:**
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

Authors
-------

* **John Brandborg** - *Initial work* - [Linkedin](https://www.linkedin.com/in/johnbrandborg/)

License
-------
This project is licensed under the MIT License - see the [LICENSE.md](https://github.com/johnbrandborg/terraform-session-token/blob/master/LICENSE) file for details