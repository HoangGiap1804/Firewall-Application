import QtQuick
import QtQuick.Controls

ListView {
        anchors.fill: parent
        model: appModel

        delegate: Rectangle {
            width: parent.width
            height: 40
            color: index % 2 === 0 ? "#f0f0f0" : "#ffffff"

            Row {
                spacing: 10
                anchors.verticalCenter: parent.verticalCenter
                Image { 
                    source: icon 
                    height: 40
                    width: 40
                }
                Text {
                    text: "(PID: " + pid + ")"
                    color: "gray"
                }
                Text {
                    text: name
                    font.bold: true
                }
            }
        }
    }
