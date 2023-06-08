#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { CdkModelDeployStack } from "../lib/model-endpoint-stack";
import { CicdPipeline } from "../lib/cicd-pipeline-stack";
import { LambdaRecordModelName } from "../lib/lambda-record-model-name-stack";

const app = new cdk.App();

// lambda record model name
const recordModelNameLambda = new LambdaRecordModelName(
  app,
  "LambdaRecordModelname",
  {}
);

// cicd pipeline stack
new CicdPipeline(app, "CiCdPipelineForSageMaker", {
  codeStartId: "531f066b-0e71-4549-90c9-97b036303ec0",
  sageMakerRole: `arn:aws:iam::${process.env.CDK_DEFAULT_ACCOUNT}:role/RoleForDataScientistUserProfile`,
  lambdaArn: recordModelNameLambda.lambadArn,
});

// sagemaker endpoint stack
new CdkModelDeployStack(app, "CdkModelDeployStack", {});
