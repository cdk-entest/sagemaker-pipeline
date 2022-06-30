import { aws_sagemaker, aws_ssm, Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";

export class CdkModelDeployStack extends Stack {
  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);

    // get model name from parameter store 
    const modelName = aws_ssm.StringParameter.fromStringParameterName(
      this,
      "PostFixModelNameConfigName",
      "HelloModelNameSps"
    ).stringValue;

    const endpointConfig = new aws_sagemaker.CfnEndpointConfig(
      this,
      "HelloCfnEndpointConfig",
      {
        endpointConfigName: modelName,
        productionVariants: [
          {
            initialVariantWeight: 1.0,
            modelName: modelName,
            variantName: "variant-name-1",
            instanceType: "ml.m4.xlarge",
            initialInstanceCount: 1,
          },
        ],
      }
    );

    // sagemaker endpoint
    new aws_sagemaker.CfnEndpoint(this, "HelloCfnEndponit", {
      endpointConfigName: endpointConfig.attrEndpointConfigName,
      endpointName: "HelloEndpointName",
    });
  }
}
