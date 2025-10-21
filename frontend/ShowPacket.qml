import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.3
import QtQml.Models
import Qt.labs.qmlmodels 1.0

Column {

        height: parent.height; width: parent.width
        property var horizontal_header_data: ["IN", "OUT", "MAC", "SRC", "DST", "LEN", "TOS", "PREC",
                                        "TTL", "ID", "PROTO", "SPT", "DPT", "LEN2"]

        property var columnWidths: [50, 50, 300, 120, 120, 50, 50, 50, 50, 50, 50, 50, 50, 50]

        RowLayout {
            spacing: 10
            height: 0.1 * parent.height
            anchors.horizontalCenter: parent.horizontalCenter
            Label { text: "Rows:" }
            TextField {
                id: rowsnumber; text: "0"; selectByMouse: true
                validator: IntValidator{}
                onTextEdited: update_table_model(parseInt(this.text))
            }
            Button {
                text: "Create Json"
                // passing table model data as string to backend
                onClicked:{
                    tableview.model.rows = JSON.parse(logModel.toList())
                    // console.log(JSON.stringify(logModel.toList()))
                }
            }
            Button {
                text: "Load Json"
                onClicked: filedialog.open() // dialog to select json file
            }
        }

        TableView {
            id: tableview
            width: 0.85 * parent.width; height: 0.8 * parent.height
            anchors.horizontalCenter: parent.horizontalCenter
            clip: true // clip content to table dimensions
            boundsBehavior: Flickable.StopAtBounds
            reuseItems: false // forces table to destroy delegates
            columnSpacing: 1 // in case of big/row spacing, you need to take care of width/height providers (to get along with it)

            // margins to vertical/horizontal headers
            leftMargin: verticalHeader.width
            topMargin: horizontalHeader.height

            // scrollbar config
            ScrollBar.horizontal: ScrollBar{
                //policy: "AlwaysOn"
            }
            ScrollBar.vertical: ScrollBar{
                //policy: "AlwaysOn"
            }
            ScrollIndicator.horizontal: ScrollIndicator { }
            ScrollIndicator.vertical: ScrollIndicator { }

            
            columnWidthProvider: function(column){ return columnWidths[column] }
            rowHeightProvider: function (column) { return 25 }

            // table horizontal header
            Row {
                id: horizontalHeader
                y: tableview.contentY
                z: 2
                Repeater {
                    model: horizontal_header_data
                    Label {
                        width: columnWidths[index]; height: 30
                        text: horizontal_header_data[index]
                        padding: 10
                        verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter
                        color: "white"
                        background: Rectangle { color: "#b5b5b5" }
                    }
                }
            }

            // table vertical header
            Column {
                id: verticalHeader
                x: tableview.contentX
                z: 2
                Repeater {
                    model: tableview.rows
                    Label {
                        width: 30; height: tableview.rowHeightProvider(modelData)
                        text: index
                        padding: 10
                        verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter
                        color: "white"
                        background: Rectangle { color: "#b5b5b5" }
                    }
                }
            }

            model: logModel
             
            // delegate: Rectangle {
            //     implicitWidth: 100
            //     implicitHeight: 50
            //     border.width: 1

            //     Text {
            //         text: model.in
            //         anchors.centerIn: parent
            //     }
            // }
            // TableViewColumn {
            //     role: "in"
            //     title: "In"
            //     width: 150
            // }

            // TableViewColumn {
            //     role: "out"
            //     title: "Out"
            //     width: 150
            // }
        }

        // TableView {
        //     id: tableview
        //     width: 0.85 * parent.width; height: 0.8 * parent.height
        //     anchors.horizontalCenter: parent.horizontalCenter
        //     clip: true // clip content to table dimensions
        //     boundsBehavior: Flickable.StopAtBounds
        //     reuseItems: false // forces table to destroy delegates
        //     columnSpacing: 1 // in case of big/row spacing, you need to take care of width/height providers (to get along with it)

        //     // margins to vertical/horizontal headers
        //     leftMargin: verticalHeader.width
        //     topMargin: horizontalHeader.height

        //     // scrollbar config
        //     ScrollBar.horizontal: ScrollBar{
        //         //policy: "AlwaysOn"
        //     }
        //     ScrollBar.vertical: ScrollBar{
        //         //policy: "AlwaysOn"
        //     }
        //     ScrollIndicator.horizontal: ScrollIndicator { }
        //     ScrollIndicator.vertical: ScrollIndicator { }

        //     // width and height providers
        //     property var columnWidths: [100, 180, 120, 100, 100]
        //     columnWidthProvider: function(column){ return columnWidths[column] }
        //     rowHeightProvider: function (column) { return 25 }

        //     // table horizontal header
        //     Row {
        //         id: horizontalHeader
        //         y: tableview.contentY
        //         z: 2
        //         Repeater {
        //             model: tableview.columns
        //             Label {
        //                 width: tableview.columnWidthProvider(modelData); height: 30
        //                 text: horizontal_header_data[index]
        //                 padding: 10
        //                 verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter
        //                 color: "white"
        //                 background: Rectangle { color: "#b5b5b5" }
        //             }
        //         }
        //     }

        //     // table vertical header
        //     Column {
        //         id: verticalHeader
        //         x: tableview.contentX
        //         z: 2
        //         Repeater {
        //             model: tableview.rows
        //             Label {
        //                 width: 30; height: tableview.rowHeightProvider(modelData)
        //                 text: index
        //                 padding: 10
        //                 verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter
        //                 color: "white"
        //                 background: Rectangle { color: "#b5b5b5" }
        //             }
        //         }
        //     }

        //     // defining model columns' roles
        //     model: TableModel {
        //         // id: tablemodel
        //         rows: [
        //             {
        //                 "name": "cat",
        //                 "color": "black"
        //             },
        //             {
        //                 "name": "dog",
        //                 "color": "brown"
        //             },
        //             {
        //                 "name": "bird",
        //                 "color": "white"
        //             }
        //         ]
        //         TableModelColumn { display: "name" }
        //         TableModelColumn { display: "color" }
        //     }

        //     // defining custom delegates and model connection
        //     delegate: Rectangle {
        //         implicitWidth: 100
        //         implicitHeight: 50
        //         border.width: 1

        //         Text {
        //             text: display
        //             anchors.centerIn: parent
        //         }
        //     }
        // }

    }


// Column {
//         anchors.fill: parent
//         spacing: 20
//         Text{
//             text: "Hello"
//         }
//         // Header cố định
//         Row {
//             id: header
//             spacing: 10

//             Header{width: 50; height: 30; t: "IN"}
//             Header{width: 50; height: 30; t: "OUT"}
//             Header{width: 300; height: 30; t: "MAC"}
//             Header{width: 120; height: 30; t: "SRC"}
//             Header{width: 120; height: 30; t: "DST"}
//             Header{width: 50; height: 30; t: "LEN"}
//             Header{width: 50; height: 30; t: "TOS"}
//             Header{width: 50; height: 30; t: "PREC"}
//             Header{width: 50; height: 30; t: "TTL"}
//             Header{width: 50; height: 30; t: "ID"}
//             Header{width: 50; height: 30; t: "PROTO"}
//             Header{width: 50; height: 30; t: "SPT"}
//             Header{width: 50; height: 30; t: "DPT"}
//             Header{width: 50; height: 30; t: "LEN2"}

//             // Rectangle { 
//             //     width: 50
//             //     height: 30
//             //     radius: 10
//             //     color: "#aecef3"
//             //     border.color: "#0078d7"
//             //     border.width: 1
//             //     Text { anchors.centerIn: parent; text: "IN" } 
//             // }
//         }

//         // Scroll các dòng log
//         ScrollView {
//             id: logScroll
//             anchors.left: parent.left
//             anchors.right: parent.right
//             anchors.top: header.bottom 
//             anchors.bottom: parent.bottom
//             clip: true

//             Flickable {
//                 id: flick
//                 contentWidth: column.width
//                 contentHeight: column.height
//                 anchors.fill: parent
//                 clip: true

//                 Column {
//                     id: column
//                     anchors.topMargin: 20
//                     spacing: 2

//                     Repeater {
//                         model: logModel
//                         Rectangle{
//                             color: "red"
//                             width: flick.width
//                             height: 30
//                             Row {
//                                 spacing: 10
//                                 Text { text: model.in; width: 50 }
//                                 Text { text: model.out; width: 50 }
//                                 Text { text: model.mac; width: 300 }
//                                 Text { text: model.src; width: 120 }
//                                 Text { text: model.dst; width: 120 }
//                                 Text { text: model.len; width: 50 }
//                                 Text { text: model.tos; width: 50 }
//                                 Text { text: model.prec; width: 50 }
//                                 Text { text: model.ttl; width: 50 }
//                                 Text { text: model.id; width: 50 }
//                                 Text { text: model.proto; width: 50 }
//                                 Text { text: model.spt; width: 50 }
//                                 Text { text: model.dpt; width: 50 }
//                                 Text { text: model.len2; width: 50 }
//                             }
//                         }
                        
//                     }
//                 }
//             }
//         }
//     }