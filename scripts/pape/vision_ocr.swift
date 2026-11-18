// On-device OCR with Apple Vision (printed + handwriting), PHI-safe: nothing leaves the Mac. (2026-11-18)
//   swiftc -O scripts/pape/vision_ocr.swift -o vision_ocr
//   vision_ocr page.tif [more images...]   -> one line per text box: "conf<TAB>text", top to bottom
import Foundation
import Vision
import AppKit

for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("ERROR cannot read \(path)"); continue
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = true
    req.recognitionLanguages = ["en-US"]
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    print("== \(path)")
    let obs = (req.results ?? []).sorted { $0.boundingBox.minY > $1.boundingBox.minY }
    for o in obs {
        if let t = o.topCandidates(1).first { print(String(format: "%.2f\t%@", t.confidence, t.string)) }
    }
}
