import QtQuick
import QtQuick.Controls 2.15
import Qt.labs.platform 1.1
import QtQuick.Layouts 1.15
import Qt.labs.platform 1.1
Column {
        anchors.centerIn: parent
        spacing: 20

       ListModel {
        id: logModel
    }

    Column {
        anchors.fill: parent
        spacing: 10
        padding: 10

        // Header cố định
        Row {
            spacing: 6
            Rectangle { 
                width: 50
                height: 30
                radius: 10
                color: "#d0e6ff"
                border.color: "#0078d7"
                border.width: 6
                Text { anchors.centerIn: parent; text: "IN" } 
            }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "OUT" } }
            Rectangle { width: 300; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "MAC" } }
            Rectangle { width: 120; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "SRC" } }
            Rectangle { width: 120; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "DST" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "LEN" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "TOS" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "PREC" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "TTL" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "ID" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "PROTO" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "SPT" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "DPT" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1; Text { anchors.centerIn: parent; text: "LEN2" } }
        }

        // Scroll area hiển thị các dòng log
        ScrollView {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            clip: true

            Column {
                id: listColumn
                width: parent.width
                spacing: 2

                Repeater {
                    model: logModel
                    Row {
                        spacing: 6
                        Rectangle { width: 50; height: 28; Text { anchors.centerIn: parent; text: model.in } }
                        Rectangle { width: 50; height: 28; Text { anchors.centerIn: parent; text: model.out } }
                        Rectangle { width: 300; height: 28; Text { anchors.centerIn: parent; text: model.mac } }
                        Rectangle { width: 120; height: 28; Text { anchors.centerIn: parent; text: model.src } }
                        Rectangle { width: 120; height: 28; Text { anchors.centerIn: parent; text: model.dst } }
                        Rectangle { width: 50; height: 28; Text { anchors.centerIn: parent; text: model.len } }
                        Rectangle { width: 50; height: 28; Text { anchors.centerIn: parent; text: model.tos } }
                        Rectangle { width: 50; height: 28; Text { anchors.centerIn: parent; text: model.prec } }
                        Rectangle { width: 50; height: 28; Text { anchors.centerIn: parent; text: model.ttl } }
                        Rectangle { width: 50; height: 28; Text { anchors.centerIn: parent; text: model.id } }
                        Rectangle { width: 50; height: 28; Text { anchors.centerIn: parent; text: model.proto } }
                        Rectangle { width: 50; height: 28; Text { anchors.centerIn: parent; text: model.spt } }
                        Rectangle { width: 50; height: 28; Text { anchors.centerIn: parent; text: model.dpt } }
                        Rectangle { width: 50; height: 28; Text { anchors.centerIn: parent; text: model.len2 } }
                    }
                }
            }
        }
    }

    // Kết nối tới Python backend
    Connections {
        target: logWatcher
        onPingFloodDetected: {
            // 'data' là object (dict) từ Python
            // append vào model để hiển thị
            logModel.append({
                "in": data.in,
                "out": data.out,
                "mac": data.mac,
                "src": data.src,
                "dst": data.dst,
                "len": data.len,
                "tos": data.tos,
                "prec": data.prec,
                "ttl": data.ttl,
                "id": data.id,
                "proto": data.proto,
                "spt": data.spt,
                "dpt": data.dpt,
                "len2": data.len2
            })
        }
    }
}