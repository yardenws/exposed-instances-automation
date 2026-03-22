resource "aws_sfn_state_machine" "this" {
  name     = var.name
  role_arn = var.role_arn

  definition = jsonencode({
    Comment = "EC2 Public Exposure — Scan and Enrich workflow"
    StartAt = "Scan"
    States = {
      Scan = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.scanner_lambda_arn
          "Payload.$"  = "$"
        }
        ResultSelector = {
          "instances.$" = "$.Payload.instances"
        }
        Next = "CheckResults"
      }
      CheckResults = {
        Type    = "Choice"
        Choices = [
          {
            Variable           = "$.instances[0]"
            IsPresent          = true
            Next               = "Enrich"
          }
        ]
        Default = "NoExposedInstances"
      }
      NoExposedInstances = {
        Type = "Succeed"
        Comment = "No publicly exposed instances found"
      }
      Enrich = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.agent_lambda_arn
          "Payload.$"  = "$"
        }
        ResultSelector = {
          "status.$" = "$.Payload.status"
        }
        End = true
      }
    }
  })

  tags = var.tags
}

resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${var.name}-schedule"
  description         = "Triggers EC2 exposure scan on a schedule"
  schedule_expression = var.schedule_expression

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "step_function" {
  rule     = aws_cloudwatch_event_rule.schedule.name
  arn      = aws_sfn_state_machine.this.arn
  role_arn = var.eventbridge_role_arn
}
