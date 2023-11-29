/*
Chatbot API Gateway
*/
resource "aws_api_gateway_rest_api" "api" {
  name        = "Chatbot API"
  description = "API for Chatbot"
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "resource" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "method" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.resource.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "integration" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.resource.id
  http_method = aws_api_gateway_method.method.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.gatekeeper_lambda.invoke_arn
}

resource "aws_api_gateway_deployment" "deployment" {
  depends_on = [aws_api_gateway_integration.integration]

  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = "prod"
}

resource "aws_lambda_permission" "apigw" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.gatekeeper_lambda.function_name
  principal     = "apigateway.amazonaws.com"
}

/*
Pushover API Gateway
*/
resource "aws_api_gateway_rest_api" "pushover_api" {
  name        = "Pushover API"
  description = "API for Pushover"
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "pushover_resource" {
  rest_api_id = aws_api_gateway_rest_api.pushover_api.id
  parent_id   = aws_api_gateway_rest_api.pushover_api.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "pushover_method" {
  rest_api_id   = aws_api_gateway_rest_api.pushover_api.id
  resource_id   = aws_api_gateway_resource.pushover_resource.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "pushover_integration" {
  rest_api_id = aws_api_gateway_rest_api.pushover_api.id
  resource_id = aws_api_gateway_resource.pushover_resource.id
  http_method = aws_api_gateway_method.pushover_method.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.pushover_lambda.invoke_arn
}

resource "aws_api_gateway_deployment" "pushover_deployment" {
  depends_on = [aws_api_gateway_integration.pushover_integration]

  rest_api_id = aws_api_gateway_rest_api.pushover_api.id
  stage_name  = "prod"
}

resource "aws_lambda_permission" "pushover_apigw" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pushover_lambda.function_name
  principal     = "apigateway.amazonaws.com"
}
