// haimtran 01 AUG 2022
// 1. connect to GitHub
// 2. build sagemaker pipeline using stepfunctions

import {
  aws_codebuild,
  aws_codepipeline,
  aws_codepipeline_actions,
  aws_iam,
  aws_lambda,
  Stack,
  StackProps,
} from "aws-cdk-lib";
import { Effect } from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";
import * as fs from "fs";
import * as path from "path";

interface CicdPipelineProps extends StackProps {
  codeStartId: string;
  sageMakerRole: string;
  lambdaArn: string;
}

export class CicdPipeline extends Stack {
  constructor(scope: Construct, id: string, props: CicdPipelineProps) {
    super(scope, id, props);

    // artifact
    const sourceOutput = new aws_codepipeline.Artifact("SourceOutput");
    const cdkBuildOutput = new aws_codepipeline.Artifact("CdkBuildOutput");
    const sageMakerBuildOutput = new aws_codepipeline.Artifact(
      "SageMakerBuildOutput"
    );

    // codebuild cdk synthesize sagemaker endpoint template
    const cdkBuildProject = new aws_codebuild.PipelineProject(
      this,
      "CdkBuildSageMakerEndpoint",
      {
        projectName: "CdkBuildSageMakerEndpoint",
        environment: {
          privileged: true,
          buildImage: aws_codebuild.LinuxBuildImage.STANDARD_5_0,
          computeType: aws_codebuild.ComputeType.MEDIUM,
        },
        buildSpec: aws_codebuild.BuildSpec.fromObject({
          version: "0.2",
          phases: {
            install: {
              commands: ["cd cdk-model-deploy", "npm install"],
            },
            build: {
              commands: ["npm run build", "npm run cdk synth -- -o dist"],
            },
          },
          artifacts: {
            "base-directory": "cdk-model-deploy/dist",
            files: ["*.template.json"],
          },
        }),
      }
    );

    // codebuild sagemaker pipepline
    const sageMakerBuild = new aws_codebuild.PipelineProject(
      this,
      "BuildSageMakerModel",
      {
        projectName: "BuildSageMakerModel",
        environment: {
          privileged: true,
          buildImage: aws_codebuild.LinuxBuildImage.STANDARD_5_0,
          computeType: aws_codebuild.ComputeType.MEDIUM,
          environmentVariables: {
            SAGEMAKER_ROLE: {
              value: props.sageMakerRole,
            },
            LAMBDA_ARN: {
              value: props.lambdaArn,
            },
          },
        },
        buildSpec: aws_codebuild.BuildSpec.fromObject({
          version: "0.2",
          phases: {
            install: {
              commands: ["pip install -r requirements.txt"],
            },
            build: {
              commands: ["python sagemaker_pipeline.py"],
            },
          },
        }),
      }
    );

    // allow running sagemker
    sageMakerBuild.addToRolePolicy(
      new aws_iam.PolicyStatement({
        effect: aws_iam.Effect.ALLOW,
        resources: ["*"],
        actions: [
          "sagemaker:*",
          "s3:*",
          "lambda:*",
          "iam:GetRole",
          "iam:PassRole",
          "states:*",
          "logs:*",
        ],
      })
    );

    // codepipeline
    const pipeline = new aws_codepipeline.Pipeline(
      this,
      "CiCdPipelineForSageMaker",
      {
        pipelineName: "CiCdPipelineForSageMaker",
        stages: [
          {
            stageName: "SourceStage",
            actions: [
              new aws_codepipeline_actions.CodeStarConnectionsSourceAction({
                actionName: "Github",
                owner: "entest-hai",
                repo: "sagemaker-pipeline",
                branch: "stepfunctions",
                connectionArn: `arn:aws:codestar-connections:${this.region}:${this.account}:connection/${props.codeStartId}`,
                output: sourceOutput,
              }),
            ],
          },
          {
            stageName: "BuildCdkStage",
            actions: [
              new aws_codepipeline_actions.CodeBuildAction({
                actionName: "BuildSagemakerEndpointStack",
                project: cdkBuildProject,
                input: sourceOutput,
                outputs: [cdkBuildOutput],
                runOrder: 1,
              }),
            ],
          },
          {
            stageName: "BuildSageMakerModel",
            actions: [
              new aws_codepipeline_actions.CodeBuildAction({
                actionName: "BuildSageMakerModel",
                project: sageMakerBuild,
                input: sourceOutput,
                outputs: [sageMakerBuildOutput],
                runOrder: 1,
              }),
            ],
          },
          {
            stageName: "DeploySageMakerModel",
            actions: [
              new aws_codepipeline_actions.CloudFormationCreateUpdateStackAction(
                {
                  actionName: "DeploySageMakerEndpoint",
                  stackName: "CdkModelDeployStack",
                  templatePath: cdkBuildOutput.atPath(
                    "CdkModelDeployStack.template.json"
                  ),
                  adminPermissions: true,
                }
              ),
            ],
          },
        ],
      }
    );
  }
}

export class LambdaRecordModelName extends Stack {
  public readonly lambadArn: string;
  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);

    const func = new aws_lambda.Function(this, "LambdaRecordModelName", {
      functionName: "LambdaRecordModeleName",
      code: aws_lambda.Code.fromInline(
        fs.readFileSync(path.join(__dirname, "./../lambda/index.py"), {
          encoding: "utf-8",
        })
      ),
      runtime: aws_lambda.Runtime.PYTHON_3_8,
      handler: "index.handler",
    });

    func.addToRolePolicy(
      new aws_iam.PolicyStatement({
        effect: Effect.ALLOW,
        actions: ["ssm:*"],
        resources: ["*"],
      })
    );

    this.lambadArn = func.functionArn;
  }
}
