"""
Hello SageMaker Pipeline
Hai Tran 30 JUN 2022
"""

import os
import json
import sagemaker
from sagemaker.estimator import Estimator
from sagemaker.workflow.steps import TrainingStep, ProcessingStep
from sagemaker.inputs import TrainingInput
from sagemaker.workflow.parameters import ParameterString, ParameterInteger
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.model import Model
from sagemaker.workflow.lambda_step import Lambda, LambdaStep


# sagemaker parameters
role = os.environ["SAGEMAKER_ROLE"]
session = sagemaker.Session()
default_bucket = session.default_bucket()
session = PipelineSession()

# data and model s3 path
model_path = f"s3://{default_bucket}/AbaloneTrain"
input_data_uri = f"s3://{default_bucket}/abalone/abalone-dataset.csv"
batch_data_uri = f"s3://{default_bucket}/abalone/abalone-dataset-batch"

# pipeline parameters
processing_instance_count = ParameterInteger(
    name="ProcessingInstanceCount", default_value=1
)

training_instance_count = ParameterInteger(
    name="TrainingInstanceCount", default_value=1
)

model_approval_status = ParameterString(
    name="ModelApprovalStatus", default_value="PendingManualApproval"
)

input_data = ParameterString(name="InputData", default_value=input_data_uri)

batch_data = ParameterString(name="BatchData", default_value=batch_data_uri)


def create_process_step() -> ProcessingStep:
    """
    create process step
    """
    sklearn_processor = SKLearnProcessor(
        framework_version="0.23-1",
        instance_type="ml.m5.xlarge",
        instance_count=processing_instance_count,
        base_job_name="sklearn-abalone-process",
        role=role,
    )
    step_process = ProcessingStep(
        name="AbaloneProcess",
        processor=sklearn_processor,
        inputs=[
            ProcessingInput(
                source=input_data_uri, destination="/opt/ml/processing/input"
            ),
        ],
        outputs=[
            ProcessingOutput(
                output_name="train",
                source="/opt/ml/processing/train",
            ),
            ProcessingOutput(
                output_name="validation", source="/opt/ml/processing/validation"
            ),
            ProcessingOutput(output_name="test", source="/opt/ml/processing/test"),
        ],
        code="preprocessing.py",
    )
    return step_process


def create_training_step(s3_train_data, s3_validation_data):
    """
    create a training step
    """
    image_uri = sagemaker.estimator.image_uris.retrieve(
        framework="xgboost",
        region="ap-southeast-1",
        version="1.0-1",
        py_version="py3",
        instance_type="ml.m5.xlarge",
    )
    xgb_train = Estimator(
        image_uri=image_uri,
        instance_type="ml.m5.xlarge",
        instance_count=training_instance_count,
        output_path=model_path,
        role=role,
    )
    xgb_train.set_hyperparameters(
        objective="reg:linear",
        num_round=50,
        max_depth=5,
        eta=0.2,
        gamma=4,
        min_child_weight=6,
        subsample=0.7,
        silent=0,
    )
    step_train = TrainingStep(
        name="AbaloneTrain",
        estimator=xgb_train,
        inputs={
            "train": TrainingInput(s3_data=s3_train_data, content_type="text/csv"),
            "validation": TrainingInput(
                s3_data=s3_validation_data, content_type="text/csv"
            ),
        },
    )
    return step_train


def create_model_batch(step_train: TrainingStep):
    """
    create model for batch transform
    """
    model = Model(
        image_uri=sagemaker.estimator.image_uris.retrieve(
            framework="xgboost",
            region="ap-southeast-1",
            version="1.0-1",
            py_version="py3",
            instance_type="ml.m5.xlarge",
        ),
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        sagemaker_session=session,
        role=role,
    )
    inputs = sagemaker.inputs.CreateModelInput(
        instance_type="ml.m5.large", accelerator_type="ml.eia1.medium"
    )
    step_create_model = sagemaker.workflow.steps.CreateModelStep(
        name="AbaloneCreateModel", model=model, inputs=inputs
    )
    return step_create_model


def create_lambda_step(model_name: str) -> LambdaStep:
    """
    create a lambda step
    """
    lambda_step = LambdaStep(
        name="LambdaRecordModelNameToParameterStore",
        lambda_func=Lambda(
            function_arn="arn:aws:lambda:ap-southeast-1:392194582387:function:RecordModelName",
            session=session,
        ),
        inputs={"model_name": model_name},
    )
    return lambda_step


def create_pipeline():
    """
    create sagemaker pipeline
    """
    # preprocessing step
    processing_step = create_process_step()
    # training step
    training_step = create_training_step(
        s3_train_data=processing_step.properties.ProcessingOutputConfig.Outputs[
            "train"
        ].S3Output.S3Uri,
        s3_validation_data=processing_step.properties.ProcessingOutputConfig.Outputs[
            "validation"
        ].S3Output.S3Uri,
    )
    # create model for batch transform
    model_step = create_model_batch(step_train=training_step)
    # lambda step
    lambda_step = create_lambda_step(model_name=model_step.properties.ModelName)
    # sagemaker pipeline
    ex_pipeline = Pipeline(
        name="AbalonePipelineTestPrintName",
        parameters=[
            processing_instance_count,
            training_instance_count,
            model_approval_status,
            input_data,
            batch_data,
        ],
        steps=[processing_step, training_step, model_step, lambda_step],
        sagemaker_session=session,
    )
    return ex_pipeline


def export_pipeline(sg_pipeline: Pipeline):
    """
    export pipeline to cfn template
    """
    # generate template json
    with open("pipeline_template.json", "w", encoding="utf-8") as file:
        json.dump(
            json.loads(sg_pipeline.definition()), file, ensure_ascii=False, indent=4
        )


def run_pipeline(sg_pipeline: Pipeline) -> None:
    """
    run pipeline
    """
    # update pipeline
    sg_pipeline.upsert(role_arn=role)
    # run pipeline
    execution = sg_pipeline.start()
    print(execution.describe())
    # wait and print model name
    execution.wait()
    # print model name
    print(execution.list_steps())


if __name__ == "__main__":
    pipeline = create_pipeline()
    run_pipeline(pipeline)
