resource "page" "platform" {
  title = "Platform spike"
  file  = "instructions/platform.md"

  activities = {
    platform = resource.task.platform
  }
}
