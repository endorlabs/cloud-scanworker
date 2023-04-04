import re
import json
import boto3
import base64

from urllib.request import urlopen, HTTPError, Request


class ServiceSecret(object):
    _secret_parse_re = re.compile('^(.*?)(@[^:]+?)?(/.*?)?:(.+)$')
    def __init__(self, secret_string):
        self.secret = secret_string

    @staticmethod
    def parse_secret(secret_string):
        match = __class__._secret_parse_re.search(secret_string)
        if not match:
            raise ValueError(f"'{secret_string}' does not match the secret string format")
        
        identity = match.group(1)
        domain = match.group(2)[1:] if match.group(2) is not None else None
        namespace = match.group(3)[1:] if match.group(3) is not None else None
        secret = match.group(4)
        return identity, domain, namespace, secret

    @property
    def secret(self):
        sstr = self.id
        domainstr = ''
        if self.domain is not None:
            domainstr = f'@{self.domain}'
        if self.namespace is not None:
            domainstr += f'/{self.namespace}'
        
        if domainstr is not None:
            sstr += domainstr
        sstr += f':{self.secret_key}'

    @secret.setter
    def secret(self, secret_string):
        (self.id, self.domain, self.namespace, self.secret_key) = __class__.parse_secret(secret_string)


class AWSSecret(object):
    def __init__(self, secret_id, region='us-east-2'):
        self._client = boto3.client(service_name='secretsmanager', region_name=region)
        self.endor = None
        self.github = None
        self.fetch_secret(secret_id)

    def fetch_secret(self, secret_id, **kwargs):
        result = self._client.get_secret_value(SecretId=secret_id, **kwargs)
        # print(f"RESULT: {pformat(result)}")
        rdict = json.loads(result['SecretString'])
        self.endor = ServiceSecret(rdict['EndorAPI'].strip())
        self.github = ServiceSecret(rdict['GithubAPI'].strip())

    @staticmethod
    def aws_api_token():
        token_req = Request('http://169.254.169.254/latest/api/token', method='PUT', headers={'X-aws-ec2-metadata-token-ttl-seconds': 21600})
        with urlopen(token_req, timeout=8) as r:
            response = r.read()

        return response

    @staticmethod
    def get_region(aws_token=None):
        if aws_token is None:
            aws_token = __class__.aws_api_token()

        metadata_request = Request('http://169.254.169.254/latest/meta-data/placement/availability-zone', headers={'X-aws-ec2-metadata-token': aws_token})
        with urlopen(metadata_request, timeout=8) as r:
            response = r.read()

        zonedata = response.decode('utf8')
        region = zonedata[:-1]
        return region
    
    @staticmethod
    def fetch_tag(*taglist):
        # TOKEN=`curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"` && curl -H "X-aws-ec2-metadata-token: $TOKEN" -v http://169.254.169.254/latest/meta-data/
        aws_token = __class__.aws_api_token()
        # print(f"AWS Token: {aws_token}")
        metadata_request = Request('http://169.254.169.254/latest/meta-data/instance-id', headers={'X-aws-ec2-metadata-token': aws_token})
        with urlopen(metadata_request, timeout=8) as r:
            response = r.read()

        instance_id = response.decode('utf8')

        region = __class__.get_region(aws_token)

        # print(f"Zone: {zonedata}, Region: {region}")

        instance = boto3.resource('ec2', region_name=region).Instance(instance_id)
        # print(f"Raw tags: {instance.tags}")
        tags = {}
        for item in instance.tags:
            tags[item['Key']] = item['Value']

        if taglist is not None:
            values = []
            for t in tags:
                if t in taglist:
                    values.append(tags[t])
            if len(values) == 1:
                return values[0]
            elif len(values) == 0:
                return None
            else:
                return values
        
        # print(f"tags for {instance_id}: {tags}")
        return tags

