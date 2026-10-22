import Foundation
import AVFoundation
import AudioToolbox

guard CommandLine.arguments.count == 4 else {
    fatalError("Usage: pitch-narration INPUT.wav UNTRIMMED.wav RECEIPT.json")
}
let sourceURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
let receiptURL = URL(fileURLWithPath: CommandLine.arguments[3])
let file = try AVAudioFile(forReading: sourceURL)
let sr: Double = 48000
let format = AVAudioFormat(standardFormatWithSampleRate: sr, channels: 1)!
let source = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(file.length))!
try file.read(into: source)
let sourceFrames = Int(source.frameLength)
let lead = 48000, tail = 96000, extraDrain = 96000
let paddedFrames = lead + sourceFrames + tail
let padded = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(paddedFrames))!
padded.frameLength = AVAudioFrameCount(paddedFrames)
padded.floatChannelData![0].initialize(repeating: 0, count: paddedFrames)
padded.floatChannelData![0].advanced(by: lead).update(from: source.floatChannelData![0], count: sourceFrames)
let engine = AVAudioEngine()
let player = AVAudioPlayerNode()
let pitch = AVAudioUnitTimePitch()
engine.attach(player)
engine.attach(pitch)
try engine.enableManualRenderingMode(.offline, format: format, maximumFrameCount: 4096)
engine.connect(player, to: pitch, format: format)
engine.connect(pitch, to: engine.mainMixerNode, format: format)
engine.mainMixerNode.outputVolume = 1
func parameter(_ id: AudioUnitParameterID) -> [String: Any] {
    var value: AudioUnitParameterValue = 0
    let result = AudioUnitGetParameter(pitch.audioUnit, id, kAudioUnitScope_Global, 0, &value)
    return ["id": Int(id), "status": Int(result), "value": Double(value)]
}
let defaults: [String: Any] = ["rate": pitch.rate, "pitch": pitch.pitch, "smoothness": pitch.overlap, "spectral_coherence": parameter(kNewTimePitchParam_EnableSpectralCoherence), "transient_preservation": parameter(kNewTimePitchParam_EnableTransientPreservation)]
pitch.rate = 1
pitch.pitch = 315
pitch.overlap = 32
pitch.auAudioUnit.renderQuality = 127
pitch.auAudioUnit.isRenderingOffline = true
let tree = pitch.auAudioUnit.parameterTree?.allParameters.map { ["address": Int($0.address), "identifier": $0.identifier, "name": $0.displayName, "value": Double($0.value), "min": Double($0.minValue), "max": Double($0.maxValue)] as [String: Any] } ?? []
let spectral = parameter(kNewTimePitchParam_EnableSpectralCoherence)
let transient = parameter(kNewTimePitchParam_EnableTransientPreservation)
guard spectral["status"] as! Int == 0, transient["status"] as! Int == 0,
      spectral["value"] as! Double == 1, transient["value"] as! Double == 1 else {
    throw NSError(domain: "TonePreview", code: 1, userInfo: [NSLocalizedDescriptionKey: "Cannot confirm the requested default phase/transient-preservation support: \(spectral), \(transient)"])
}
player.scheduleBuffer(padded, at: nil, options: [])
engine.prepare()
try engine.start()
player.play()
let renderFrames = paddedFrames + extraDrain
let buffer = AVAudioPCMBuffer(pcmFormat: engine.manualRenderingFormat, frameCapacity: 4096)!
let output = try AVAudioFile(forWriting: outputURL, settings: format.settings, commonFormat: .pcmFormatFloat32, interleaved: false)
var written = 0
var cannotDoRetries = 0
var statuses: [String: Int] = [:]
while written < renderFrames {
    let request = AVAudioFrameCount(min(4096, renderFrames - written))
    let status = try engine.renderOffline(request, to: buffer)
    statuses[String(status.rawValue), default: 0] += 1
    if buffer.frameLength > 0 {
        try output.write(from: buffer)
        written += Int(buffer.frameLength)
    }
    if status == .cannotDoInCurrentContext {
        cannotDoRetries += 1
        if cannotDoRetries > 100 { throw NSError(domain: "TonePreview", code: 2, userInfo: [NSLocalizedDescriptionKey: "Manual render stalled"])}
    } else if status == .error {
        throw NSError(domain: "TonePreview", code: 3, userInfo: [NSLocalizedDescriptionKey: "Manual render error"])
    }
}
let receipt: [String: Any] = ["source_frames": sourceFrames, "source_seconds": Double(sourceFrames)/sr, "sample_rate": sr, "channels": 1, "lead_padding_frames": lead, "tail_padding_frames": tail, "extra_drain_frames": extraDrain, "written_untrimmed_frames": written, "rate": pitch.rate, "pitch_cents": pitch.pitch, "smoothness": pitch.overlap, "render_quality": pitch.auAudioUnit.renderQuality, "rendering_offline": pitch.auAudioUnit.isRenderingOffline, "reported_latency_seconds": pitch.latency, "reported_au_latency_seconds": pitch.auAudioUnit.latency, "reported_tail_time_seconds": pitch.auAudioUnit.tailTime, "defaults_before_setting": defaults, "spectral_coherence": spectral, "transient_preservation": transient, "parameter_tree": tree, "render_status_counts": statuses, "authorized_pitch_treatment": true]
let data = try JSONSerialization.data(withJSONObject: receipt, options: [.prettyPrinted, .sortedKeys])
try data.write(to: receiptURL)
print(String(data: data, encoding: .utf8)!)
player.stop()
engine.stop()
