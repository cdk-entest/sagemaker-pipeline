"""
haimtran 01 AUG 2022
lambda write to system parameter store
record model name
pipelines-y6tfth6zwzda-AbaloneCreateModel-CraPCbgDZF
"""

import boto3

ssmClient = boto3.client("ssm")


def handler(event, context):
    """
    update model name into system parameter store
    """
    ssmClient.put_parameter(
        Name="HelloModelNameSps",
        Description="sagemaker model name",
        Value="pipelines-y6tfth6zwzda-AbaloneCreateModel-CraPCbgDZF",
        Overwrite=True,
    )
    return {"message": "hello"}


handler(event={}, context={})
