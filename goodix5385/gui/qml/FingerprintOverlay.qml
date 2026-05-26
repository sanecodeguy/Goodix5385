import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Shapes 1.15

Window {
    id: overlay
    width: 420
    height: 520
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    color: "transparent"
    modality: Qt.ApplicationModal

    property bool isEnrolling: false
    property string fingerName: ""
    property string status: "Place your finger on the sensor"
    property bool success: false
    property int scanCount: 0

    signal startEnroll(string finger)
    signal startVerify()
    signal cancel()

    Rectangle {
        anchors.centerIn: parent
        width: 380
        height: 480
        radius: 24
        color: "#1e1e2e"
        border.color: "#313244"
        border.width: 1

        layer.enabled: true
        layer.effect: DropShadow {
            transparentBorder: true
            radius: 32
            samples: 64
            color: "#80000000"
        }

        Column {
            anchors.centerIn: parent
            spacing: 24
            width: parent.width - 60

            Item { width: 1; height: 1 }

            Rectangle {
                id: iconFrame
                anchors.horizontalCenter: parent.horizontalCenter
                width: 160
                height: 160
                radius: 80
                color: "#181825"
                border.color: overlay.success ? "#a6e3a1" : (overlay.scanCount > 0 ? "#89b4fa" : "#313244")
                border.width: 2

                Behavior on border.color {
                    ColorAnimation { duration: 300 }
                }

                Shape {
                    anchors.centerIn: parent
                    width: 100
                    height: 120
                    antialiasing: true

                    ShapePath {
                        strokeColor: overlay.success ? "#a6e3a1" : (overlay.scanCount > 0 ? "#89b4fa" : "#6c7086")
                        strokeWidth: 3
                        fillColor: "transparent"
                        capStyle: ShapePath.RoundCap
                        joinStyle: ShapePath.RoundJoin

                        PathSvg { path: "M50 10 C22 10 10 30 10 50 L10 80 C10 100 22 110 30 110 L30 50 C30 35 40 25 50 25 C60 25 70 35 70 50 L70 110 C78 110 90 100 90 80 L90 50 C90 30 78 10 50 10Z" }
                    }

                    ShapePath {
                        strokeColor: overlay.success ? "#a6e3a1" : (overlay.scanCount > 0 ? "#89b4fa" : "#6c7086")
                        strokeWidth: 2.5
                        fillColor: "transparent"
                        capStyle: ShapePath.RoundCap

                        PathSvg { path: "M50 40 L50 65 M35 50 L65 50" }
                    }

                    ShapePath {
                        strokeColor: overlay.success ? "#a6e3a1" : "#89b4fa"
                        strokeWidth: 2
                        fillColor: "transparent"
                        capStyle: ShapePath.RoundCap
                        visible: overlay.scanCount > 0

                        PathSvg { path: "M30 75 Q50 90 70 75" }
                    }
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: 60; height: 60; radius: 30
                    color: overlay.success ? "#a6e3a1" : "#89b4fa"
                    opacity: overlay.scanCount > 0 ? 0.15 : 0
                    scale: overlay.scanCount > 0 ? 1 : 0.5

                    Behavior on opacity { NumberAnimation { duration: 300 } }
                    Behavior on scale { NumberAnimation { duration: 300 } }
                }

                SequentialAnimation {
                    running: overlay.scanCount > 0 && !overlay.success
                    loops: Animation.Infinite

                    NumberAnimation {
                        target: iconFrame
                        property: "scale"
                        from: 1.0; to: 1.03
                        duration: 600
                        easing.type: Easing.InOutSine
                    }
                    NumberAnimation {
                        target: iconFrame
                        property: "scale"
                        from: 1.03; to: 1.0
                        duration: 600
                        easing.type: Easing.InOutSine
                    }
                }
            }

            Text {
                id: titleText
                anchors.horizontalCenter: parent.horizontalCenter
                text: overlay.isEnrolling ? "Enrolling Fingerprint" : "Verify Fingerprint"
                color: "#cdd6f4"
                font.pixelSize: 18
                font.weight: Font.DemiBold
                font.family: "Segoe UI, SF Pro, sans-serif"
            }

            Text {
                id: fingerText
                anchors.horizontalCenter: parent.horizontalCenter
                text: overlay.fingerName
                color: "#a6adc8"
                font.pixelSize: 13
                visible: overlay.fingerName.length > 0
                font.family: "Segoe UI, SF Pro, sans-serif"
            }

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 280; height: 36; radius: 18
                color: overlay.success ? "#1e3a2f" : (overlay.scanCount > 0 ? "#1e2a4a" : "#181825")
                border.color: overlay.success ? "#a6e3a1" : (overlay.scanCount > 0 ? "#89b4fa" : "#313244")
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: overlay.status
                    color: overlay.success ? "#a6e3a1" : (overlay.scanCount > 0 ? "#89b4fa" : "#6c7086")
                    font.pixelSize: 13
                    font.family: "Segoe UI, SF Pro, sans-serif"
                }
            }

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 8
                visible: overlay.isEnrolling

                Repeater {
                    model: 8
                    Rectangle {
                        width: 28; height: 4; radius: 2
                        color: index < overlay.scanCount ? "#89b4fa" : "#313244"
                        Behavior on color { ColorAnimation { duration: 200 } }
                    }
                }
            }

            Button {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Cancel"
                flat: true
                contentItem: Text {
                    text: parent.text
                    color: "#f38ba8"
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    color: parent.hovered ? "#2a1e24" : "transparent"
                    radius: 8
                }
                onClicked: overlay.cancel()
            }

            Item { width: 1; height: 1 }
        }
    }

    function reset() {
        scanCount = 0
        success = false
        status = "Place your finger on the sensor"
    }
}
