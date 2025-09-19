import QtQuick 2.15
import QtQuick.Controls 2.15

Column {
        anchors.fill: parent
        spacing: 20
        // Header cố định
        Row {
            id: header
            spacing: 10
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "IN" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "OUT" } }
            Rectangle { width: 300; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "MAC" } }
            Rectangle { width: 120; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "SRC" } }
            Rectangle { width: 120; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "DST" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "LEN" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "TOS" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "PREC" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "TTL" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "ID" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "PROTO" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "SPT" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "DPT" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "LEN2" } }
        }

        // Scroll các dòng log
        ScrollView {
            id: logScroll
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: header.bottom 
            anchors.bottom: parent.bottom
            clip: true

            Flickable {
                id: flick
                contentWidth: column.width
                contentHeight: column.height
                anchors.fill: parent
                clip: true

                Column {
                    id: column
                    anchors.topMargin: 20
                    spacing: 2

                    Repeater {
                        model: logModel
                        Rectangle{
                            color: "red"
                            width: flick.width
                            height: 30
                            Row {
                                spacing: 10
                                Text { text: model.in; width: 50 }
                                Text { text: model.out; width: 50 }
                                Text { text: model.mac; width: 300 }
                                Text { text: model.src; width: 120 }
                                Text { text: model.dst; width: 120 }
                                Text { text: model.len; width: 50 }
                                Text { text: model.tos; width: 50 }
                                Text { text: model.prec; width: 50 }
                                Text { text: model.ttl; width: 50 }
                                Text { text: model.id; width: 50 }
                                Text { text: model.proto; width: 50 }
                                Text { text: model.spt; width: 50 }
                                Text { text: model.dpt; width: 50 }
                                Text { text: model.len2; width: 50 }
                            }
                        }
                        
                    }
                }
            }
        }
    }