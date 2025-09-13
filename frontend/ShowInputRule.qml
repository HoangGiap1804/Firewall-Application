import QtQuick 2.15
import QtQuick.Controls 2.15

Column {
        anchors.fill: parent
        spacing: 5

        // Header cố định
        Row {
            id: header
            spacing: 10
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "Num" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "Pkts" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "Bytes" } }
            Rectangle { width: 100; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "Target" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "Prot" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "Opt" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "IN" } }
            Rectangle { width: 50; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "OUT" } }
            Rectangle { width: 120; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "Source" } }
            Rectangle { width: 120; height: 30; color: "lightgray"; border.width: 1
                Text { anchors.centerIn: parent; text: "Destination" } }
        }

        // Scroll chứa dữ liệu
        ScrollView {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: header.bottom
            anchors.bottom: parent.bottom

            Flickable {
                anchors.fill: parent
                contentWidth: column.width
                contentHeight: column.height
                clip: true

                Column {
                    id: column
                    spacing: 2

                    Repeater {
                        model: inputRuleModel 
                        Row {
                            spacing: 10
                            Text { text: model.num; width: 50 }
                            Text { text: model.pkts; width: 50 }
                            Text { text: model.bytes; width: 50 }
                            Text { text: model.target; width: 100 }
                            Text { text: model.prot; width: 50 }
                            Text { text: model.opt; width: 50 }
                            Text { text: model.in; width: 50 }
                            Text { text: model.out; width: 50 }
                            Text { text: model.source; width: 120 }
                            Text { text: model.destination; width: 120 }

                            Button { 
                                text: "DELETE"
                                width: 100
                                onClicked: {
                                    inputRuleModel.deleteRule(model.num)
                                }
                            }
                        }
                    }
                }
            }
        }
    }