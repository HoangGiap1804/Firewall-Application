import QtQuick 2.15
import QtQuick.Controls 2.15

ListView {
        anchors.fill: parent
        model: logAttackModel

        delegate: Rectangle {
            width: parent.width
            height: 40
            color: prefix == "PING_FLOOD" ? "#ffcccc" :
                   prefix == "SYN_FLOOD" ? "#ffe0b3" :
                   prefix == "SSH_BRUTEFORCE" ? "#ff9999" :
                   prefix == "PORT_SCAN" ? "#d9b3ff" :
                   "#f2f2f2"

            Row {
                spacing: 10
                Text { text: time; font.bold: true }
                Text { text: prefix; font.pixelSize: 14; color: "red" }
                Text { text: msg; font.pixelSize: 13 }
            }
        }
    }