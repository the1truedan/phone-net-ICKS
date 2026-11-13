// R.E.:⁄ (re-fraction) popup, first test (2026-11-13). Draws a branded µ box over everything on the main display
// for a few seconds, then fades. The Mac draws it, so the TV/monitor never changes input.
//   swiftc -O scripts/wifi/re_fraction_popup.swift -o /tmp/re_fraction_popup && /tmp/re_fraction_popup "<line 1>" "<line 2>" [seconds]
import AppKit

let args = CommandLine.arguments
let line1 = args.count > 1 ? args[1] : "µ test · front door"
let line2 = args.count > 2 ? args[2] : DateFormatter.localizedString(from: Date(), dateStyle: .none, timeStyle: .short)
let hold = args.count > 3 ? Double(args[3]) ?? 6 : 6

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let screen = NSScreen.main!.frame
let w: CGFloat = 620, h: CGFloat = 190, margin: CGFloat = 60
let frame = NSRect(x: screen.maxX - w - margin, y: screen.maxY - h - margin - 30, width: w, height: h)
let panel = NSPanel(contentRect: frame, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
panel.level = .screenSaver
panel.isOpaque = false
panel.backgroundColor = .clear
panel.hasShadow = true
panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
panel.ignoresMouseEvents = true

let cyan = NSColor(red: 0.43, green: 0.91, blue: 1.0, alpha: 1)
let card = NSView(frame: NSRect(x: 0, y: 0, width: w, height: h))
card.wantsLayer = true
card.layer?.backgroundColor = NSColor(red: 0.03, green: 0.04, blue: 0.06, alpha: 0.96).cgColor
card.layer?.cornerRadius = 18
card.layer?.borderWidth = 2
card.layer?.borderColor = cyan.withAlphaComponent(0.55).cgColor
card.layer?.shadowColor = cyan.cgColor
card.layer?.shadowOpacity = 0.6
card.layer?.shadowRadius = 22
card.layer?.shadowOffset = .zero

// the µ box: a small isometric-feeling square with the µ glyph
let box = NSView(frame: NSRect(x: 26, y: 35, width: 120, height: 120))
box.wantsLayer = true
box.layer?.backgroundColor = NSColor(red: 0.07, green: 0.08, blue: 0.11, alpha: 1).cgColor
box.layer?.cornerRadius = 12
box.layer?.borderWidth = 1.5
box.layer?.borderColor = NSColor(red: 0.17, green: 0.2, blue: 0.27, alpha: 1).cgColor
let mu = NSTextField(labelWithString: "µ")
mu.font = NSFont(name: "Georgia", size: 84) ?? .systemFont(ofSize: 84)
mu.textColor = cyan
mu.alignment = .center
mu.frame = NSRect(x: 0, y: 6, width: 120, height: 104)
box.addSubview(mu)
card.addSubview(box)

let tag = NSTextField(labelWithString: "R.E.:⁄  re-fraction")
tag.font = .monospacedSystemFont(ofSize: 15, weight: .medium)
tag.textColor = NSColor(white: 0.55, alpha: 1)
tag.frame = NSRect(x: 172, y: 128, width: 420, height: 22)
let t1 = NSTextField(labelWithString: line1)
t1.font = .systemFont(ofSize: 30, weight: .semibold)
t1.textColor = NSColor(white: 0.93, alpha: 1)
t1.frame = NSRect(x: 172, y: 78, width: 430, height: 40)
let t2 = NSTextField(labelWithString: line2)
t2.font = .monospacedSystemFont(ofSize: 22, weight: .regular)
t2.textColor = cyan
t2.frame = NSRect(x: 172, y: 40, width: 430, height: 30)
[tag, t1, t2].forEach { card.addSubview($0) }

panel.contentView = card
panel.alphaValue = 0
panel.orderFrontRegardless()
let sent = Date()
NSAnimationContext.runAnimationGroup({ ctx in ctx.duration = 0.35; panel.animator().alphaValue = 1 })
DispatchQueue.main.asyncAfter(deadline: .now() + hold) {
    NSAnimationContext.runAnimationGroup({ ctx in ctx.duration = 0.8; panel.animator().alphaValue = 0 }, completionHandler: {
        print(String(format: "RE_FRACTION_POPUP shown %.1f s on main display, then faded", Date().timeIntervalSince(sent)))
        app.terminate(nil)
    })
}
app.run()
