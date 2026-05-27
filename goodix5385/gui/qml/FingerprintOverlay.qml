import QtQuick 2.15
import QtQuick.Controls 2.15

Window {
    id: overlay
    width: 440
    height: 540
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    color: "transparent"
    modality: Qt.ApplicationModal

    property bool isEnrolling: false
    property string fingerName: ""
    property string status: "Place your finger on the sensor"
    property bool success: false
    property int scanCount: 0
    property bool retryMode: false
    property bool scanning: false   // true while a scan attempt is in progress

    property int _restX: 0

    // Pulse state for the SVG glow
    property real ridgeOpacity: 0.18
    property color ridgeColor: "#89b4fa"
    property real glowRadius: 0.0

    signal cancel()

    // ── Auto-reset from no-match back to scanning ─────────────────────────────
    Timer {
        id: resetTimer
        interval: 1200
        onTriggered: {
            if (overlay.retryMode) {
                overlay.retryMode = false
                overlay.status = "Place your finger on the sensor"
            }
        }
    }

    // ── Shake on no-match ────────────────────────────────────────────────────
    SequentialAnimation {
        id: shakeAnim
        PropertyAction { target: overlay; property: "_restX"; value: overlay.x }
        NumberAnimation { target: overlay; property: "x"; to: overlay._restX - 10; duration: 35 }
        NumberAnimation { target: overlay; property: "x"; to: overlay._restX + 10; duration: 35 }
        NumberAnimation { target: overlay; property: "x"; to: overlay._restX - 7;  duration: 35 }
        NumberAnimation { target: overlay; property: "x"; to: overlay._restX + 7;  duration: 35 }
        NumberAnimation { target: overlay; property: "x"; to: overlay._restX - 3;  duration: 35 }
        NumberAnimation { target: overlay; property: "x"; to: overlay._restX + 3;  duration: 35 }
        NumberAnimation { target: overlay; property: "x"; to: overlay._restX;      duration: 35 }
    }

    // ── Flash / pulse on any status change ──────────────────────────────────
    SequentialAnimation {
        id: scanFlash
        NumberAnimation { target: overlay; property: "ridgeOpacity"; to: 0.85; duration: 80;  easing.type: Easing.OutQuad }
        NumberAnimation { target: overlay; property: "ridgeOpacity"; to: 0.18; duration: 320; easing.type: Easing.InCubic }
    }

    // ── Glow pulse while idle / scanning ────────────────────────────────────
    SequentialAnimation {
        id: idlePulse
        running: !overlay.success
        loops: Animation.Infinite
        NumberAnimation { target: overlay; property: "glowRadius"; to: 1.0; duration: 1200; easing.type: Easing.InOutSine }
        NumberAnimation { target: overlay; property: "glowRadius"; to: 0.0; duration: 1200; easing.type: Easing.InOutSine }
    }

    // ── Success burst ────────────────────────────────────────────────────────
    SequentialAnimation {
        id: successBurst
        NumberAnimation { target: overlay; property: "ridgeOpacity"; to: 1.0; duration: 60 }
        NumberAnimation { target: overlay; property: "ridgeOpacity"; to: 0.6; duration: 400; easing.type: Easing.OutCubic }
    }

    onRetryModeChanged: { if (retryMode) { shakeAnim.start(); resetTimer.restart() } }
    onScanCountChanged: { scanFlash.start() }
    onSuccessChanged:   { if (success) { idlePulse.stop(); successBurst.start() } }

    // ── Background card ──────────────────────────────────────────────────────
    Rectangle {
        id: card
        anchors.centerIn: parent
        width: 400; height: 500
        radius: 28
        color: "#0d0d12"
        border.color: overlay.success  ? "#a6e3a1"
                    : overlay.retryMode ? "#f38ba8"
                    : "#1e1e2e"
        border.width: 1.5

        Behavior on border.color { ColorAnimation { duration: 300 } }

        // Subtle top-edge highlight
        Rectangle {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width * 0.5
            height: 1
            color: overlay.success  ? "#a6e3a180"
                 : overlay.retryMode ? "#f38ba880"
                 : "#ffffff18"
            Behavior on color { ColorAnimation { duration: 300 } }
        }

        Column {
            anchors.centerIn: parent
            width: parent.width - 48
            spacing: 28

            // ── Title ────────────────────────────────────────────────────────
            Column {
                width: parent.width
                spacing: 6

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: overlay.isEnrolling ? "Enroll Fingerprint" : "Verify Fingerprint"
                    color: "#e8eaf6"
                    font.pixelSize: 19
                    font.weight: Font.Medium
                    font.letterSpacing: 0.4
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: overlay.fingerName
                    color: "#555870"
                    font.pixelSize: 12
                    visible: overlay.fingerName.length > 0
                    font.letterSpacing: 0.3
                }
            }

            // ── Fingerprint Lottie canvas ──────────────────────────────────
            Item {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 180; height: 200

                // Glow halo behind the print
                Rectangle {
                    anchors.centerIn: parent
                    width:  140 + overlay.glowRadius * 30
                    height: 140 + overlay.glowRadius * 30
                    radius: width / 2
                    color: "transparent"
                    border.color: overlay.success  ? "#a6e3a1"
                                : overlay.retryMode ? "#f38ba8"
                                : "#89b4fa"
                    border.width: 1
                    opacity: 0.08 + overlay.glowRadius * 0.12
                    Behavior on border.color { ColorAnimation { duration: 300 } }
                }
                Rectangle {
                    anchors.centerIn: parent
                    width:  110 + overlay.glowRadius * 20
                    height: 110 + overlay.glowRadius * 20
                    radius: width / 2
                    color: "transparent"
                    border.color: overlay.success  ? "#a6e3a1"
                                : overlay.retryMode ? "#f38ba8"
                                : "#89b4fa"
                    border.width: 1
                    opacity: 0.06 + overlay.glowRadius * 0.10
                    Behavior on border.color { ColorAnimation { duration: 300 } }
                }

                Canvas {
                    id: fpCanvas
                    anchors.centerIn: parent
                    width: 130; height: 130

                    property int _scanCount: 0
                    property bool _success: false
                    property bool _retryMode: false

                    property var _dep: [overlay.scanCount, overlay.success, overlay.retryMode, overlay.isEnrolling]
                    on_DepChanged: {
                        _scanCount = overlay.scanCount
                        _success = overlay.success
                        _retryMode = overlay.retryMode
                        requestPaint()
                    }
                    Component.onCompleted: requestPaint()

                    onPaint: {
                        var ctx = getContext("2d")
                        var w = width, h = height
                        ctx.clearRect(0, 0, w, h)

                        var progress = Math.min(_scanCount / 8, 1.0)
                        if (_success) progress = 1.0

                        var cx = w / 2, cy = h / 2
                        var maxR = Math.min(w, h) / 2 - 10

                        ctx.strokeStyle = _success ? "#a6e3a1"
                                          : _retryMode ? "#f38ba8"
                                          : "#89b4fa"
                        ctx.lineWidth = 2.5
                        ctx.lineCap = "round"

                        var rings = 6
                        for (var i = 0; i < rings; i++) {
                            var t = (i + 1) / (rings + 1)
                            var ringR = maxR * t
                            var frac = Math.max(0, Math.min(1, (progress * rings - i)))
                            if (frac <= 0) continue
                            var startA = -Math.PI / 2
                            var endA = startA + Math.PI * 2 * frac
                            ctx.beginPath()
                            ctx.arc(cx, cy, ringR, startA, endA)
                            ctx.stroke()
                        }

                        // short center line
                        if (progress > 0.5) {
                            var cl = maxR * 0.2
                            ctx.beginPath()
                            ctx.moveTo(cx, cy - cl)
                            ctx.lineTo(cx, cy + cl)
                            ctx.stroke()
                        }
                    }
                }
            }

            // ── Status pill ──────────────────────────────────────────────────
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(parent.width, statusText.implicitWidth + 40)
                height: 34
                radius: 17
                color: overlay.success  ? "#0d2218"
                     : overlay.retryMode ? "#1f0c0e"
                     : "#0f1020"
                border.color: overlay.success  ? "#a6e3a140"
                            : overlay.retryMode ? "#f38ba840"
                            : "#89b4fa30"
                border.width: 1

                Behavior on color       { ColorAnimation { duration: 250 } }
                Behavior on border.color{ ColorAnimation { duration: 250 } }

                Text {
                    id: statusText
                    anchors.centerIn: parent
                    text: overlay.status
                    color: overlay.success  ? "#a6e3a1"
                         : overlay.retryMode ? "#f38ba8"
                         : "#8892b0"
                    font.pixelSize: 12
                    font.letterSpacing: 0.2
                }
            }

            // ── Enroll progress dots ─────────────────────────────────────────
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 10
                visible: overlay.isEnrolling

                Repeater {
                    model: 8
                    Rectangle {
                        width: index < overlay.scanCount ? 24 : 8
                        height: 4
                        radius: 2
                        color: index < overlay.scanCount ? "#89b4fa" : "#1e2030"

                        Behavior on width { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }
                        Behavior on color { ColorAnimation { duration: 200 } }
                    }
                }
            }

            // ── Action button (Cancel while scanning, Done on success) ────────
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 160; height: 40
                radius: 20
                color: btnMouse.containsMouse
                       ? (overlay.success ? "#1a3d2a" : "#161828")
                       : "transparent"
                border.color: overlay.success ? "#a6e3a160" : "#89b4fa50"
                border.width: 1

                Behavior on color { ColorAnimation { duration: 150 } }

                Text {
                    anchors.centerIn: parent
                    text: overlay.success ? "Done" : "Cancel"
                    color: overlay.success ? "#a6e3a1" : "#555870"
                    font.pixelSize: 13
                    font.letterSpacing: 0.5
                }

                MouseArea {
                    id: btnMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: overlay.success ? overlay.hide() : overlay.cancel()
                }
            }
        }
    }

    function reset() {
        scanCount  = 0
        success    = false
        retryMode  = false
        scanning   = false
        status     = "Place your finger on the sensor"
    }
}
