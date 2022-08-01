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
  codeStartId: "f8487d2f-fbf7-4604-8d4c-e672b7d38cf4",
  sageMakerRole: `arn:aws:iam::${process.env.CDK_DEFAULT_ACCOUNT}:role/RoleForNoteBook`,
  lambdaArn: recordModelNameLambda.lambadArn,
});

// sagemaker endpoint stack
new CdkModelDeployStack(app, "CdkModelDeployStack", {});
