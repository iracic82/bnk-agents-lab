resource "layout" "spike" {
  column {
    width = "35"

    instructions {}
  }

  column {
    tab "console" {
      title  = "Console"
      target = resource.terminal.console
      active = true
    }
  }
}
