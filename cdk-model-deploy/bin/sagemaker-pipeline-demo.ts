#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { CdkModelDeployStack } from "../lib/model-endpoint-stack";
import { CicdPipeline, SageMakerRoleStack } from "../lib/cicd-pipeline-stack";
import { LambdaRecordModelName } from "../lib/lambda-record-model-name-stack";

// codestart id to connect to github
const codeStartId = "efbf9e3c-f0e0-476f-8416-462468c96ec6";

const app = new cdk.App();

// sagemake role
const sagemaker = new SageMakerRoleStack(app, "SageMakerRoleStack", {});

// lambda record model name
const recordModelNameLambda = new LambdaRecordModelName(
  app,
  "LambdaRecordModelname",
  {}
);

// cicd pipeline stack
const pipeline = new CicdPipeline(app, "CiCdPipelineForSageMaker", {
  codeStartId: codeStartId,
  sageMakerRole: sagemaker.role.roleArn,
  lambdaArn: recordModelNameLambda.lambadArn,
});

// sagemaker endpoint stack
// for pipeline deploy
new CdkModelDeployStack(app, "CdkModelDeployStack", {});

pipeline.addDependency(sagemaker);
pipeline.addDependency(recordModelNameLambda);
