import json
import pulumi
import pulumi_aws as aws
import pulumi_aws_apigateway as apigateway


queue = aws.sqs.Queue('cloud-dead-drop-ids', fifo_queue=False)

bucket = aws.s3.Bucket('cloud-dead-drop', acl='private', 
    lifecycle_rules=[aws.s3.BucketLifecycleRuleArgs(
        enabled=True,
        expiration=aws.s3.BucketLifecycleRuleExpirationArgs(days=14)
        )]
    )

env = aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "NOTIFICATIONS_QUEUE": queue.url,
            "UPLOAD_BUCKET": bucket.id
        }
    )

five_minute_schedule = aws.cloudwatch.EventRule('every-5-minutes',
    schedule_expression='rate(5 minutes)'
)

one_minute_schedule = aws.cloudwatch.EventRule('every-minute',
    schedule_expression='rate(1 minute)' 
)

role = aws.iam.Role("cloud-drop-role", 
    assume_role_policy=json.dumps({
        'Version': '2012-10-17',
        'Statement': [{
            'Action': 'sts:AssumeRole',
            'Effect': 'Allow',
            'Principal': {'Service': ['lambda.amazonaws.com']}
        }]
    }),
    managed_policy_arns=[
        aws.iam.ManagedPolicy.AWS_LAMBDA_BASIC_EXECUTION_ROLE
    ])

policy = aws.iam.Policy('cloud-drop-policy',
    policy=pulumi.Output.all(bucket=bucket.arn, queue=queue.arn).apply(
        lambda args: json.dumps({
            'Version': '2012-10-17',
            'Statement': [{
                'Effect': 'Allow',
                'Action': [
                    's3:GetObject',
                    's3:PutObject'
                ],
                'Resource': f'{args['bucket']}/ids/*',
            },
            {
                'Effect': 'Allow',
                'Action': [
                    's3:GetObject',
                    's3:PutObject'
                ],
                'Resource': f'{args['bucket']}/uploads/*',
            },{
                'Effect': 'Allow',
                'Action': [
                    'sqs:SendMessage',
                    'sqs:ReceiveMessage',
                    'sqs:DeleteMessage',
                    'sqs:DeleteMessageBatch'
                ],
                'Resource': args['queue'],
            }],
        }))
)

aws.iam.RolePolicyAttachment('policy-attachment',
    role=role.name,
    policy_arn=policy.arn.apply(lambda arn: arn)
)

generate_upload_url = aws.lambda_.Function("generate_upload_url",
    runtime="python3.9",
    environment=env,
    handler="handler.generate_upload_url",
    role=role.arn,
    code=pulumi.FileArchive("./function"))

register_id = aws.lambda_.Function("register_id",
    runtime="python3.9",
    environment=env,
    handler="handler.register_id",
    role=role.arn,
    code=pulumi.FileArchive("./function"))

publish_ids = aws.lambda_.Function("publish_ids",
    runtime="python3.9",
    environment=env,
    handler="handler.publish_ids",
    role=role.arn,
    code=pulumi.FileArchive("./function"))

maybe_publish_decoy = aws.lambda_.Function("maybe_publish_decoy",
    runtime="python3.9",
    environment=env,
    handler="handler.maybe_publish_decoy",
    role=role.arn,
    code=pulumi.FileArchive("./function"))

decoy_target = aws.cloudwatch.EventTarget('maybe-publish-decoy',
    rule=one_minute_schedule.name,
    arn=maybe_publish_decoy.arn
)

publish_target = aws.cloudwatch.EventTarget('publish-pending-ids',
    rule=five_minute_schedule.name,
    arn=publish_ids.arn
)

api = apigateway.RestAPI("cloud-dead-drop-api",
  routes=[
    apigateway.RouteArgs(path="/upload-url", 
                         method=apigateway.Method.GET, 

                         event_handler=generate_upload_url),
    apigateway.RouteArgs(path="/register-id", 
                         method=apigateway.Method.PUT, 
                         event_handler=register_id),
                         
  ])

pulumi.export("url", api.url)
