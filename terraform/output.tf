output "chatbot_api_url" {
  description = "Chatbot API Gateway URL"
  value       = "https://${aws_api_gateway_rest_api.api.id}.execute-api.eu-west-1.amazonaws.com/prod/"
}

output "pushover_api_url" {
  description = "Pushover API Gateway URL"
  value       = "https://${aws_api_gateway_rest_api.pushover_api.id}.execute-api.eu-west-1.amazonaws.com/prod/"
}
