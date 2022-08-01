#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { CdkModelDeployStack } from "../lib/model-endpont-stack";
import { CicdPipeline } from "../lib/cicd-pipeline";

const app = new cdk.App();

// sagemaker endpoint stack
new CdkModelDeployStack(app, "CdkModelDeployStack", {});

// cicd pipeline stack
new CicdPipeline(app, "CiCdPipelineForSageMaker", {});
