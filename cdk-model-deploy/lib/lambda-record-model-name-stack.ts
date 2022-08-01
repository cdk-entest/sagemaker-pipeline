import { aws_iam, aws_lambda, Stack, StackProps } from "aws-cdk-lib";
import { Effect } from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";
import * as fs from "fs";
import * as path from "path";

export class LambdaRecordModelName extends Stack {
  public readonly lambadArn: string;
  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);

    const func = new aws_lambda.Function(this, "LambdaRecordModelName", {
      functionName: "LambdaRecordModelName",
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
