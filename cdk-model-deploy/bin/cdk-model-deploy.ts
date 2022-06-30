#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { CdkModelDeployStack } from "../lib/cdk-model-deploy-stack";
import { CicdPipeline } from "../lib/cicd-pipeline";

const app = new cdk.App();

// sagemaker endpoint stack 
new CdkModelDeployStack(app, "CdkModelDeployStack", {});

// cicd pipeline stack 
new CicdPipeline(app, "CiCdPipelineForSageMaker", {});