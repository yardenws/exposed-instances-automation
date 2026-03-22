resource "aws_apigatewayv2_api" "this" {
  name          = var.name
  protocol_type = "HTTP"

  tags = var.tags
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true

  tags = var.tags
}

# --- Mitigation route: POST /mitigate ---

resource "aws_apigatewayv2_integration" "mitigate" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.mitigation_lambda_invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "mitigate" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "POST /mitigate"
  target    = "integrations/${aws_apigatewayv2_integration.mitigate.id}"
}

resource "aws_lambda_permission" "mitigate" {
  statement_id  = "AllowAPIGatewayInvokeMitigate"
  action        = "lambda:InvokeFunction"
  function_name = var.mitigation_lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*/mitigate"
}

# --- Escalation route: POST /escalate ---

resource "aws_apigatewayv2_integration" "escalate" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.escalation_lambda_invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "escalate" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "POST /escalate"
  target    = "integrations/${aws_apigatewayv2_integration.escalate.id}"
}

resource "aws_lambda_permission" "escalate" {
  statement_id  = "AllowAPIGatewayInvokeEscalate"
  action        = "lambda:InvokeFunction"
  function_name = var.escalation_lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*/escalate"
}

# --- Slack interactions route: POST /slack/interactions ---
# Routes to the Agent Lambda which parses the Slack interaction payload,
# verifies the signing secret, and dispatches to mitigate/escalate.

resource "aws_apigatewayv2_integration" "slack_interactions" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.agent_lambda_invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "slack_interactions" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "POST /slack/interactions"
  target    = "integrations/${aws_apigatewayv2_integration.slack_interactions.id}"
}

resource "aws_lambda_permission" "slack_interactions" {
  statement_id  = "AllowAPIGatewayInvokeSlackInteractions"
  action        = "lambda:InvokeFunction"
  function_name = var.agent_lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*/slack/interactions"
}
