"""
cdk/med_safety_stack.py
Full CDK stack: VPC → Neptune → Lambda → API Gateway → S3 + CloudFront (static site)
"""
import os
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_neptune_alpha as neptune,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cf,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    Duration,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct


class MedSafetyStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ─── 1. VPC ──────────────────────────────────────────────────────────
        # Neptune must live inside a VPC. Lambda needs to be in the same VPC.
        vpc = ec2.Vpc(self, "MedSafetyVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )

        # ─── 2. Security Groups ───────────────────────────────────────────────
        neptune_sg = ec2.SecurityGroup(self, "NeptuneSG",
            vpc=vpc,
            description="Allow Lambda to access Neptune",
            allow_all_outbound=True
        )

        lambda_sg = ec2.SecurityGroup(self, "LambdaSG",
            vpc=vpc,
            description="Lambda security group",
            allow_all_outbound=True
        )

        # Allow Lambda → Neptune on port 8182
        neptune_sg.add_ingress_rule(
            peer=lambda_sg,
            connection=ec2.Port.tcp(8182),
            description="Neptune Gremlin from Lambda"
        )

        # ─── 3. Neptune Cluster ───────────────────────────────────────────────
        neptune_cluster = neptune.DatabaseCluster(self, "MedSafetyNeptune",
            vpc=vpc,
            instance_type=neptune.InstanceType.T3_MEDIUM,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[neptune_sg],
            removal_policy=RemovalPolicy.DESTROY,  # Change to RETAIN for production
            iam_authentication=False
        )

        # ─── 4. S3 Bucket for Neptune Bulk Load ──────────────────────────────
        data_bucket = s3.Bucket(self, "MedSafetyDataBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # Upload the Neptune CSV files automatically
        s3deploy.BucketDeployment(self, "DeployNeptuneData",
            sources=[s3deploy.Source.asset("../data", exclude=["*.py"])],
            destination_bucket=data_bucket,
            destination_key_prefix="neptune-data/"
        )

        # ─── 5. IAM Role for Neptune to read from S3 ─────────────────────────
        neptune_s3_role = iam.Role(self, "NeptuneS3Role",
            assumed_by=iam.ServicePrincipal("rds.amazonaws.com"),
            description="Allows Neptune to load data from S3"
        )
        data_bucket.grant_read(neptune_s3_role)

        # ─── 6. Lambda Layer (gremlinpython) ─────────────────────────────────
        # We package gremlinpython as a layer so Lambda doesn't need to reinstall it
        gremlin_layer = _lambda.LayerVersion(self, "GremlinLayer",
            code=_lambda.Code.from_asset("../lambda/layer"),  # created in Step 5 of guide
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="gremlinpython for Neptune queries"
        )

        # ─── 7. Lambda Function ───────────────────────────────────────────────
        lambda_role = iam.Role(self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ]
        )

        # Allow Lambda to call Bedrock
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"]
        ))

        chat_lambda = _lambda.Function(self, "ChatLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../lambda"),
            timeout=Duration.seconds(30),
            memory_size=512,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[lambda_sg],
            layers=[gremlin_layer],
            role=lambda_role,
            environment={
                "NEPTUNE_ENDPOINT": neptune_cluster.cluster_endpoint.hostname,
                "NEPTUNE_PORT": "8182",
                "BEDROCK_REGION": self.region,
            }
        )

        # ─── 8. API Gateway ───────────────────────────────────────────────────
        api = apigw.RestApi(self, "MedSafetyApi",
            rest_api_name="MedSafetyAPI",
            description="Medication Safety Chatbot API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["POST", "OPTIONS"],
                allow_headers=["Content-Type"]
            )
        )

        chat_resource = api.root.add_resource("chat")
        chat_resource.add_method(
            "POST",
            apigw.LambdaIntegration(chat_lambda)
        )

        # ─── 9. S3 + CloudFront for Static Website ────────────────────────────
        website_bucket = s3.Bucket(self, "WebsiteBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        distribution = cf.Distribution(self, "MedSafetyDistribution",
            default_behavior=cf.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(website_bucket),
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cf.CachePolicy.CACHING_DISABLED,  # Disable cache for dynamic feel
            ),
            default_root_object="index.html",
            error_responses=[
                cf.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html"
                )
            ]
        )

        # Deploy frontend files to S3
        s3deploy.BucketDeployment(self, "DeployWebsite",
            sources=[s3deploy.Source.asset("../frontend")],
            destination_bucket=website_bucket,
            distribution=distribution,
            distribution_paths=["/*"]
        )

        # ─── 10. Outputs ──────────────────────────────────────────────────────
        CfnOutput(self, "WebsiteURL",
            value=f"https://{distribution.domain_name}",
            description="Your MedSafe chatbot website URL"
        )
        CfnOutput(self, "ApiEndpoint",
            value=api.url,
            description="API Gateway endpoint (save this!)"
        )
        CfnOutput(self, "NeptuneEndpoint",
            value=neptune_cluster.cluster_endpoint.hostname,
            description="Neptune cluster endpoint"
        )
        CfnOutput(self, "DataBucketName",
            value=data_bucket.bucket_name,
            description="S3 bucket for Neptune bulk load data"
        )
        CfnOutput(self, "NeptuneS3RoleArn",
            value=neptune_s3_role.role_arn,
            description="IAM Role ARN to use for Neptune bulk load"
        )
