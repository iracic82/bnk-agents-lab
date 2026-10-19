resource "lab" "main" {
  title       = "AI agents run the AI factory: NVIDIA Run:ai, NeMo Agent Toolkit and BNK 2.4"
  description = "Spike: checks that a Labs 2.0 sandbox can host BNK 2.4 and open-source Run:ai."

  settings {
    timelimit {
      duration = "2h"
    }

    idle {
      enabled = true
      timeout = "30m"
    }
  }

  layout = resource.layout.spike

  content {
    chapter "spike" {
      title = "Platform spike"

      page "platform" {
        reference = resource.page.platform
      }
    }
  }
}
