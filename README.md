# Endor Labs AWS Secretless Scanner

----

> **NOTE:** this is a _reference_ implementation and is currently _unsupported_

----

A Python3 module and command-line tool that acquires GitHub and Endor Labs credentials from AWS Secrets Manager in order to scan all supported repos in your GitHub organization.

## Installation

1. Generate API keys:
    1. classic key for GitHub
    2. Key ID and Secret for EndorLabs
2. Create an AWS Secret in Secrets Manager named `EndorLabs_ScanWorkerAuth`, and provide two Key-Value pairs:
    1. `GithubAPI`: `USERNAME@github.com/ORGNAME:OAUTH_KEY`
    2. `EndorAPI`: `KEYID@endorlabs.com/NAMESPACE:KEY_SECRET`
3. Copy the ARN of the Secret
4. Create an EC2 instance with an official Ubuntu 22.04 LTS (Jammy Jellyfish) AMI for your region (you can find [a searchable list on ubuntu.com](https://cloud-images.ubuntu.com/locator/ec2/)):
    1. An IAM Policy that allows describing the instance (`AmazonEC2ReadOnlyAccess` works well) and access to the ARN of `EndorLabs_ScanWorkerAuth`
    2. A tag named `EndorLabs_SecretName`, with the value `EndorLabs_ScanWorkerAuth`
    3. User data containing the contents of [`ubuntu_setup.bash`](ubuntu_setup.bash)
        * **NOTE:** make appropriate modifications for your environment; the EC2 instance should be able to build your target packages for best results
5. Launch the instance -- after launch is complete, it will begin installing requirements and automatically scanning your supported repos

We strongly recommend a `t3.xlarge` or comparable instance; analysis performed during scan is CPU and RAM intensive.


## Configuring

The `su ubuntu -c 'endor-venv/bin/endor-scanworker'` command can take command-line switches to alter behavior. Notable switches:

 * `--aws-secret-name` use a specific name (not ARN) for the secret; if you provide this, you will not need to provide the secret name in a tag
 * `--aws-secret-tag` (default=`EndorLabs_SecretName`) change the name of the tag we use to get the name of the secret
 * `--lang` only scan repos flagged as having this (supported) language. Specify multiple times to scan multiple languages. Default is all supported languages.
 * `--results` provide a filesystem path where results JSON documents will be saved; they will be named `<orgname>_<reponame>.json`; if not provided, JSON documents are not preserved and results will be available through the Endor Labs UI or API only


 ## Troubleshooting

 Run the command interactively, or redirect STDERR to a file to get status and error messages. Usual causes of failures are:

 * network egress rules prohibiting access to tools or API endpoints
 * misconfiguration of EC2 tags or resources
 * correct build environment to build your projects is not available in the instance
