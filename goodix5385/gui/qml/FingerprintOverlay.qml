import QtQuick 2.15
import QtQuick.Controls 2.15

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

                Item {
                    anchors.centerIn: parent
                    width: 90
                    height: 110

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 0
                        width: 50
                        height: 60
                        radius: 25
                        color: "transparent"
                        border.color: overlay.success ? "#a6e3a1" : (overlay.scanCount > 0 ? "#89b4fa" : "#6c7086")
                        border.width: 3
                    }

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 48
                        width: 30
                        height: 18
                        radius: 15
                        color: "transparent"
                        border.color: overlay.success ? "#a6e3a1" : (overlay.scanCount > 0 ? "#89b4fa" : "#6c7086")
                        border.width: 2
                    }

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: 22
                        width: 14
                        height: 14
                        radius: 7
                        color: overlay.success ? "#a6e3a1" : "#89b4fa"
                        opacity: 0.15
                        visible: overlay.scanCount > 0
                    }
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
                anchors.horizontalCenter: parent.horizontalCenter
                text: overlay.isEnrolling ? "Enrolling Fingerprint" : "Verify Fingerprint"
                color: "#cdd6f4"
                font.pixelSize: 18
                font.weight: Font.DemiBold
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: overlay.fingerName
                color: "#a6adc8"
                font.pixelSize: 13
                visible: overlay.fingerName.length > 0
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
