"""
haimtran 01 AUG 2022
build a sagemaker pipeline using stepfunctions SDK for data science
1. preprocessing data
2. train model
3. create model
4. lambda record model name into system parameter store
step 4 is for deployment with the latest model name
"""
import json
import uuid
import stepfunctions
from stepfunctions.inputs import ExecutionInput
from stepfunctions import steps
import sagemaker
from sagemaker.estimator import Estimator
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.processing import ProcessingInput, ProcessingOutput


# get configuration
with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)
    print(config)

# sagemaker
session = sagemaker.Session()
default_bucket = session.default_bucket()

# preprocessing intput
model_path = f"s3://{default_bucket}/AbaloneTrain"
input_data_uri = f"s3://{default_bucket}/abalone/abalone-dataset.csv"
input_code_uri = f"s3://{default_bucket}/abalone/preprocessing.py"
batch_data_uri = f"s3://{default_bucket}/abalone/abalone-dataset-batch"

# preprocessing output
processing_output_path = f"s3://{default_bucket}/abalone/processing-output/"

# train input paths
s3_train_data = f"s3://{default_bucket}/abalone/processing-output"
s3_validation_data = f"s3://{default_bucket}/abalone/processing-output"
train_output_path = f"s3://{default_bucket}/AbaloneTrain"

# dynamic unique job name, model name
execution_input = ExecutionInput(
    schema={
        "PreprocessingJobName": str,
        "TrainingJobName": str,
        "LambdaFunctionName": str,
        "ModelName": str,
    }
)

# create processing step
def create_process_step() -> stepfunctions.steps.ProcessingStep:
    """
    create process step
    """
    sklearn_processor = SKLearnProcessor(
        framework_version="0.23-1",
        instance_type="ml.m5.xlarge",
        instance_count=1,
        base_job_name="sklearn-abalone-process",
        role=config["SAGEMAKER_ROLE"],
    )
    step_process = stepfunctions.steps.ProcessingStep(
        state_id="PreprocessingData",
        processor=sklearn_processor,
        job_name=execution_input["PreprocessingJobName"],
        inputs=[
            ProcessingInput(
                input_name="train-data-input",
                source=input_data_uri,
                destination="/opt/ml/processing/input",
            ),
            ProcessingInput(
                input_name="train-code-input",
                source=input_code_uri,
                destination="/opt/ml/processing/code",
            ),
        ],
        outputs=[
            ProcessingOutput(
                output_name="train-data-output",
                source="/opt/ml/processing/train",
                destination=processing_output_path,
            ),
            ProcessingOutput(
                output_name="validation-data-output",
                source="/opt/ml/processing/validation",
                destination=processing_output_path,
            ),
            ProcessingOutput(
                output_name="test-data-output",
                source="/opt/ml/processing/test",
                destination=processing_output_path,
            ),
        ],
        container_entrypoint=["python3", "/opt/ml/processing/code/preprocessing.py"],
    )
    return step_process


# create a training step
def create_training_step():
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
        instance_count=1,
        output_path=train_output_path,
        role=config["SAGEMAKER_ROLE"],
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

    step_train = stepfunctions.steps.TrainingStep(
        state_id="TrainingModel",
        estimator=xgb_train,
        data={
            "train": sagemaker.TrainingInput(s3_train_data, content_type="text/csv"),
            "validation": sagemaker.TrainingInput(
                s3_validation_data, content_type="text/csv"
            ),
        },
        job_name=execution_input["TrainingJobName"],
    )
    return step_train


def create_model_batch(training_step: stepfunctions.steps.TrainingStep):
    """
    create model for batch transform
    """
    model_step = stepfunctions.steps.ModelStep(
        state_id="SaveModel",
        model=training_step.get_expected_model(),
        model_name=execution_input["ModelName"],
    )
    return model_step


def create_lambda_step(model_name: str) -> steps.LambdaStep:
    """
    lambda step to record model name
    """
    lambda_step = stepfunctions.steps.LambdaStep(
        state_id="LambdaStep",
        parameters={
            "FunctionName": execution_input["LambdaFunctionName"],
            "Payload": {"model_name": model_name},
        },
    )
    return lambda_step


def create_workflow() -> stepfunctions.workflow.Workflow:
    """
    create a state machine for ml pipeline
    """
    # processing step
    processing_step = create_process_step()
    # training step
    training_step = create_training_step()
    # create model step
    model_step = create_model_batch(training_step=training_step)
    # lambda step
    lambda_step = create_lambda_step(model_name=execution_input["ModelName"])
    # workflow
    definition = stepfunctions.steps.Chain(
        [processing_step, training_step, model_step, lambda_step]
    )
    workflow = stepfunctions.workflow.Workflow(
        name="StepFunctionWorkFlow",
        definition=definition,
        role=config["WORKFLOW_ROLE"],
        execution_input=execution_input,
    )
    return workflow


if __name__ == "__main__":
    ml_workflow = create_workflow()
    print(ml_workflow.definition)
    ml_workflow.create()
    ml_workflow.execute(
        inputs={
            "PreprocessingJobName": f"PreprocessingJobName{uuid.uuid4()}",
            "TrainingJobName": f"TrainingJobName{uuid.uuid4()}",
            "LambdaFunctionName": "LambdaRecordModelName",
            "ModelName": f"ModelName{uuid.uuid4()}",
        }
    )
    # ml_workflow.delete()
