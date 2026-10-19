resource "layout" "spike" {
  column {
    width = "35"

    instructions {}
  }

  column {
    tab "gpu" {
      title  = "gpu"
      target = resource.terminal.gpu
      active = true
    }

    tab "dpu" {
      title  = "dpu"
      target = resource.terminal.dpu
    }
  }
}
