/*
Shared lambda policies
*/
resource "aws_iam_role" "lambda_execution_role" {
  name = "lambda_execution_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Effect = "Allow",
        Sid    = ""
      }
    ]
  })
}

resource "aws_iam_policy" "iam_policy_for_logs" {
  name        = "aws_iam_policy_for_terraform_aws_lambda_role"
  path        = "/"
  description = "AWS IAM Policy for managing aws lambda role"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:*",
        Effect   = "Allow"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_role_policy_attachment" "lambda_log_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.iam_policy_for_logs.arn
}

resource "aws_iam_role_policy_attachment" "lambda_eventbridge_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEventBridgeFullAccess"
}

/*
Gatekeeper lambda
*/
resource "aws_lambda_function" "gatekeeper_lambda" {
  filename         = "${path.module}/../lambda/gatekeeper/package/gatekeeper.zip"
  function_name    = "gatekeeper_lambda"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256("${path.module}/../lambda/gatekeeper/package/gatekeeper.zip")

  environment {
    variables = {
      SLACK_SIGNING_SECRET = var.SLACK_SIGNING_SECRET
    }
  }
}

resource "aws_lambda_permission" "allow_eventbridge_gatekeeper" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.gatekeeper_lambda.arn
  principal     = "events.amazonaws.com"
}

resource "aws_lambda_permission" "allow_cloudwatch_gatekeeper" {
  statement_id  = "AllowCloudWatchInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.gatekeeper_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.keep_gatekeeper_lambda_warm.arn
}

/*
Opsgenie lambda
*/
resource "aws_lambda_function" "opsgenie_lambda" {
  filename         = "${path.module}/../lambda/opsgenie/package/opsgenie.zip"
  function_name    = "opsgenie_lambda"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256("${path.module}/../lambda/opsgenie/package/opsgenie.zip")

  environment {
    variables = {
      SLACK_BOT_TOKEN = var.SLACK_BOT_TOKEN
      OPSGENIE_URL    = var.OPSGENIE_URL
      OPSGENIE_TOKEN  = var.OPSGENIE_TOKEN
    }
  }
}

resource "aws_lambda_permission" "allow_eventbridge_opsgenie" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.opsgenie_lambda.arn
  principal     = "events.amazonaws.com"
}

resource "aws_lambda_permission" "allow_cloudwatch_opsgenie" {
  statement_id  = "AllowCloudWatchInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.opsgenie_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.keep_opsgenie_lambda_warm.arn
}

/*
Qchain IAM role
*/
resource "aws_iam_role" "qchain_lambda_role" {
  name = "qchain_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Effect = "Allow",
        Sid    = ""
      }
    ]
  })
}

resource "aws_iam_policy" "iam_policy_for_prod_a" {
  name        = "aws_iam_policy_for_assume_prod_a"
  path        = "/"
  description = "AWS IAM Policy for assume prod A"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "sts:AssumeRole"
        ],
        Resource = "arn:aws:iam::324006799445:role/killswitch",
        Effect   = "Allow"
      }
    ]
  })
}

resource "aws_iam_policy" "iam_policy_for_vpc_permissions" {
  name        = "aws_iam_policy_for_vpc_permissions"
  path        = "/"
  description = "AWS IAM Policy for vpc permissions"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ],
        Resource = "*",
        Effect   = "Allow"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "qchain_lambda_assume_prod_a" {
  role       = aws_iam_role.qchain_lambda_role.name
  policy_arn = aws_iam_policy.iam_policy_for_vpc_permissions.arn
}

resource "aws_iam_role_policy_attachment" "qchain_lambda_vpc_permissions" {
  role       = aws_iam_role.qchain_lambda_role.name
  policy_arn = aws_iam_policy.iam_policy_for_prod_a.arn
}

resource "aws_iam_role_policy_attachment" "qchain_lambda_s3_access" {
  role       = aws_iam_role.qchain_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_role_policy_attachment" "qchain_lambda_log_access" {
  role       = aws_iam_role.qchain_lambda_role.name
  policy_arn = aws_iam_policy.iam_policy_for_logs.arn
}

resource "aws_iam_role_policy_attachment" "qchain_lambda_eventbridge_access" {
  role       = aws_iam_role.qchain_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEventBridgeFullAccess"
}

/*
Qchain lambda
*/
resource "aws_lambda_function" "qchain_lambda" {
  filename         = "${path.module}/../lambda/qchain/package/qchain.zip"
  function_name    = "qchain_lambda"
  role             = aws_iam_role.qchain_lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256("${path.module}/../lambda/qchain/package/qchain.zip")

  vpc_config {
    subnet_ids         = ["subnet-0ec7a0624d86bb0d5", "subnet-049707e0b7e5a064f"]
    security_group_ids = ["sg-0f02d69f5e6ae1906"]
  }

  environment {
    variables = {
      SLACK_BOT_TOKEN         = var.SLACK_BOT_TOKEN
      QCHAIN_AWS_REGION       = var.QCHAIN_AWS_REGION
      QCHAIN_EKS_CLUSTER_NAME = var.QCHAIN_EKS_CLUSTER_NAME
      QCHAIN_EKS_NAMESPACE    = var.QCHAIN_EKS_NAMESPACE
    }
  }
}

resource "aws_lambda_permission" "allow_eventbridge_qchain" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.qchain_lambda.arn
  principal     = "events.amazonaws.com"
}

resource "aws_lambda_permission" "allow_cloudwatch_qchain" {
  statement_id  = "AllowCloudWatchInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.qchain_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.keep_qchain_lambda_warm.arn
}

/*
Pushover lambda
*/
resource "aws_lambda_function" "pushover_lambda" {
  filename         = "${path.module}/../lambda/pushover/package/pushover.zip"
  function_name    = "pushover_lambda"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256("${path.module}/../lambda/pushover/package/pushover.zip")

  environment {
    variables = {
      AUTH_HEADER               = var.AUTH_HEADER
      PUSHOVER_URL              = var.PUSHOVER_URL
      PUSHOVER_TOKEN            = var.PUSHOVER_TOKEN
      PUSHOVER_WEB3_GROUP       = var.PUSHOVER_WEB3_GROUP
      PUSHOVER_HUB_GROUP        = var.PUSHOVER_HUB_GROUP
      PUSHOVER_TRADING_GROUP    = var.PUSHOVER_TRADING_GROUP
      PUSHOVER_BLOCKCHAIN_GROUP = var.PUSHOVER_BLOCKCHAIN_GROUP
      PUSHOVER_MPC_GROUP        = var.PUSHOVER_MPC_GROUP
      PUSHOVER_DEVOPS_GROUP     = var.PUSHOVER_DEVOPS_GROUP
      PUSHOVER_STAFF_GROUP      = var.PUSHOVER_STAFF_GROUP
      PUSHOVER_SECURITY_GROUP   = var.PUSHOVER_SECURITY_GROUP
      OPSGENIE_URL              = var.OPSGENIE_URL
      OPSGENIE_TOKEN            = var.OPSGENIE_TOKEN
      OPSGENIE_WEB3_TEAM        = var.OPSGENIE_WEB3_TEAM
      OPSGENIE_HUB_TEAM         = var.OPSGENIE_HUB_TEAM
      OPSGENIE_TRADING_TEAM     = var.OPSGENIE_TRADING_TEAM
      OPSGENIE_BLOCKCHAIN_TEAM  = var.OPSGENIE_BLOCKCHAIN_TEAM
      OPSGENIE_MPC_TEAM         = var.OPSGENIE_MPC_TEAM
      OPSGENIE_DEVOPS_TEAM      = var.OPSGENIE_DEVOPS_TEAM
      OPSGENIE_STAFF_TEAM       = var.OPSGENIE_STAFF_TEAM
      OPSGENIE_SECURITY_TEAM    = var.OPSGENIE_SECURITY_TEAM
      QCHAIN_AWS_REGION         = var.QCHAIN_AWS_REGION
      QCHAIN_EKS_CLUSTER_NAME   = var.QCHAIN_EKS_CLUSTER_NAME
      QCHAIN_EKS_NAMESPACE      = var.QCHAIN_EKS_NAMESPACE
    }
  }
}

/*
Eventbridge rules
*/
resource "aws_cloudwatch_event_rule" "opsgenie_event_rule" {
  name        = "OpsgenieEventRule"
  description = "Capture specific events and route to Lambda for /sre command"

  event_pattern = jsonencode({
    "source" : ["gatekeeper"],
    "detail-type" : ["Slack Command Invoked"],
    "detail" : {
      "route" : ["/sre"]
    }
  })
}

resource "aws_cloudwatch_event_target" "opsgenie_event_target" {
  rule      = aws_cloudwatch_event_rule.opsgenie_event_rule.name
  target_id = "SendToLambda"
  arn       = aws_lambda_function.opsgenie_lambda.arn
}

resource "aws_cloudwatch_event_rule" "qchain_event_rule" {
  name        = "QchainEventRule"
  description = "Capture specific events and route to Lambda for /qchain command"

  event_pattern = jsonencode({
    "source" : ["gatekeeper"],
    "detail-type" : ["Slack Command Invoked"],
    "detail" : {
      "route" : ["/qchain"]
    }
  })
}

resource "aws_cloudwatch_event_target" "qchain_event_target" {
  rule      = aws_cloudwatch_event_rule.qchain_event_rule.name
  target_id = "SendToLambda"
  arn       = aws_lambda_function.qchain_lambda.arn
}

/*
Keep lambdas warm otherwise slack will timeout
*/

resource "aws_cloudwatch_event_rule" "keep_opsgenie_lambda_warm" {
  name                = "KeepOpsgenieLambdaWarm"
  description         = "Trigger Opsgenie Lambda every 5 minutes to keep it warm"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "opsgenie_lambda_target" {
  rule      = aws_cloudwatch_event_rule.keep_opsgenie_lambda_warm.name
  target_id = "OpsgenieLambdaWarm"
  arn       = aws_lambda_function.opsgenie_lambda.arn
}

resource "aws_cloudwatch_event_rule" "keep_gatekeeper_lambda_warm" {
  name                = "KeepGatekeeperLambdaWarm"
  description         = "Trigger Gatekeeper Lambda every 5 minutes to keep it warm"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "gatekeeper_lambda_target" {
  rule      = aws_cloudwatch_event_rule.keep_gatekeeper_lambda_warm.name
  target_id = "OpsgenieLambdaWarm"
  arn       = aws_lambda_function.gatekeeper_lambda.arn
}

resource "aws_cloudwatch_event_rule" "keep_qchain_lambda_warm" {
  name                = "KeepQchainLambdaWarm"
  description         = "Trigger Qchain Lambda every 5 minutes to keep it warm"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "qchain_lambda_target" {
  rule      = aws_cloudwatch_event_rule.keep_qchain_lambda_warm.name
  target_id = "QchainLambdaWarm"
  arn       = aws_lambda_function.qchain_lambda.arn
}
