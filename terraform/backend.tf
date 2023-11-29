terraform {
  backend "s3" {
    bucket  = "tf-chatbot"
    key     = "env/prod/terraform.tfstate"
    region  = "eu-west-1"
    encrypt = true
  }
}
