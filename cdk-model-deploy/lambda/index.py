"""
haimtran 01 AUG 2022
lambda write sagemaker model name to system parameter store
"""

import json
import boto3

ssmClient = boto3.client("ssm")


def handler(event, context):
    """
    write model name to ssm
    """
    # parse model name
    model_name = event["model_name"]
    # ssm client
    ssm = boto3.client("ssm")
    # write model name to parameter store
    ssm.put_parameter(Name="HelloModelNameSps", Value=model_name, Overwrite=True,  Type='String')
    return {"statusCode": 200, "body": json.dumps("Hello from Lambda!")}


handler(event={"model_name": "example"}, context={})
