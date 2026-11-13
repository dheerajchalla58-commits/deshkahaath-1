import Cocoa
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate {
    var window: NSWindow!
    var webView: WKWebView!
    var server: Process?
    var portFile: URL!
    var attempts = 0

    func applicationDidFinishLaunching(_ notification: Notification) {
        guard let resources = Bundle.main.resourceURL else { NSApp.terminate(nil); return }
        let python = resources.appendingPathComponent("python/bin/python3")
        let project = resources.appendingPathComponent("project", isDirectory: true)
        portFile = FileManager.default.temporaryDirectory.appendingPathComponent("desh-\(UUID().uuidString).port")
        let process = Process()
        process.executableURL = python
        process.arguments = [project.appendingPathComponent("mac/desktop_server.py").path]
        process.currentDirectoryURL = project
        var env = ProcessInfo.processInfo.environment
        env["DESH_PORT_FILE"] = portFile.path
        env["PYTHONPATH"] = project.path
        env["PYTHONUNBUFFERED"] = "1"
        process.environment = env
        do { try process.run(); server = process }
        catch {
            showError("Could not start the local server. Please reinstall the app.")
            return
        }
        let configuration = WKWebViewConfiguration()
        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1200, height: 800),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
        window.title = "Desh Ke Haath"
        window.contentView = webView
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        waitForServer()
    }

    func waitForServer() {
        if let text = try? String(contentsOf: portFile, encoding: .ascii),
           let port = Int(text.trimmingCharacters(in: .whitespacesAndNewlines)),
           let url = URL(string: "http://127.0.0.1:\(port)/") {
            webView.load(URLRequest(url: url))
            return
        }
        attempts += 1
        if attempts >= 120 || server?.isRunning == false {
            showError("The local server could not start. Please reinstall the app.")
            return
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) { self.waitForServer() }
    }

    func showError(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "Desh Ke Haath"
        alert.informativeText = message
        alert.runModal()
        NSApp.terminate(nil)
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if let url = navigationAction.request.url, let host = url.host,
           host != "127.0.0.1" && host != "localhost" {
            NSWorkspace.shared.open(url)
            decisionHandler(.cancel)
            return
        }
        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.canChooseDirectories = parameters.allowsDirectories
        panel.canChooseFiles = true
        panel.begin { response in completionHandler(response == .OK ? panel.urls : nil) }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationWillTerminate(_ notification: Notification) {
        if let process = server, process.isRunning { process.terminate() }
        if let file = portFile { try? FileManager.default.removeItem(at: file) }
    }
}

let application = NSApplication.shared
let delegate = AppDelegate()
application.delegate = delegate
application.setActivationPolicy(.regular)
application.run()
