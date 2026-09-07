// =============================================================================
// HYDRA-UMC-OS-REBUILDER - Qt Quick visual desktop shell: Main.qml
// Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
// GPL-3.0 - see LICENSE
// =============================================================================
// Same real colors/typography AND the same styled component set
// (GameButton/GameCombo/GameCheck/GameField/MetricCard/AboutInfoRow, the
// animated header mark, the gradient background, the About dialog) as
// HYDRA-UMC-UPDATER's own Main.qml - ported deliberately, not just the
// color tokens, so this ecosystem's PC tools genuinely share one visual
// language rather than one sharing the palette and the other staying
// default Qt Controls. No project row, build phase or status here is
// hard-coded: qt_gui.py's RebuilderBridge supplies real ecosystem
// discovery and real build-pipeline progress to this presentation.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.VectorImage

ApplicationWindow {
    id: window
    width: 1300
    height: 860
    minimumWidth: 980
    minimumHeight: 640
    visible: true
    visibility: Window.Maximized
    title: "HYDRA-UMC OS Rebuilder"
    color: "#07111e"

    property string languageTick: backend.language
    property color canvasColor: "#07111e"
    property color panel: "#101d30"
    property color panelAlt: "#14253b"
    property color border: "#294965"
    property color textPrimary: "#edf7ff"
    property color textMuted: "#91a8bd"
    property color cyan: "#38d4e6"
    property color blue: "#397dff"
    property color green: "#43db9b"
    property color amber: "#f3ba55"
    property color red: "#ee6b80"

    // Static, client-side - the real, fixed phase sequence build_image()
    // (image_builder.py) reports via its own BuildProgress.phase, in
    // order. Used only to render an honest checkpoint list (done/active/
    // pending) from backend.buildPhase - never a guessed percentage.
    readonly property var buildPhases: ["download", "decompress", "mount", "install", "firstboot-config", "unmount", "finalize"]

    // Real Build Target state - "local" only ever makes sense when
    // backend.platformOk (this same machine is Linux+root); defaults to
    // "remote" on a Windows dev machine, where local can never work, so
    // the panel opens already showing the option that's actually usable.
    property string buildTarget: backend.platformOk ? "local" : "remote"
    property string remotePreset: "cm5"
    property string remoteAuthMethod: "key"

    function ui(key) {
        // Keeping this dependency makes all bound labels refresh when the
        // language changes, without a duplicated QML translation catalogue.
        var ignored = languageTick
        return backend.text(key)
    }

    // Real, discrete progress (0.0-1.0) for the progress bar below the
    // build log - one honest fraction per real phase `backend.buildPhase`
    // has actually reached in buildPhases above, never a smoothly-animated
    // fake percentage. 0 both before any build has started and once one
    // finishes and buildBusy goes false again (buildPhase itself is left
    // showing the last real phase reached, for the label next to the bar).
    property real buildProgressFraction: {
        if (!backend.buildBusy) return 0.0
        var index = buildPhases.indexOf(backend.buildPhase)
        return index < 0 ? 0.0 : (index + 1) / buildPhases.length
    }

    function checkpointState(phaseKey) {
        var current = buildPhases.indexOf(backend.buildPhase)
        var mine = buildPhases.indexOf(phaseKey)
        if (current < 0) return "pending"
        if (mine < current) return "done"
        if (mine === current) return backend.buildBusy ? "active" : "done"
        return "pending"
    }

    function checkpointColor(state) {
        if (state === "done") return green
        if (state === "active") return cyan
        if (state === "failed") return red
        return border
    }

    component LabelText: Text {
        color: window.textPrimary
        // Bahnschrift gives Windows the intended angular/technical character;
        // Qt falls back cleanly to the system sans family on Linux/CM5.
        font.family: "Bahnschrift"
        font.pixelSize: 12
        renderType: Text.QtRendering
    }

    component SectionPanel: Rectangle {
        color: window.panel
        radius: 16
        border.width: 1
        border.color: window.border
    }

    component MetricCard: Rectangle {
        id: metric
        required property string caption
        required property string value
        required property color accent
        color: window.panelAlt
        radius: 11
        height: 72
        border.width: 1
        border.color: Qt.rgba(accent.r, accent.g, accent.b, 0.35)
        Row {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10
            Rectangle { width: 4; height: parent.height; radius: 2; color: metric.accent }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                LabelText { text: metric.value; color: metric.accent; font.pixelSize: 22; font.bold: true }
                LabelText { text: metric.caption; color: window.textMuted; font.pixelSize: 11 }
            }
        }
    }

    // Qt Controls use the platform style by default, which can mean dark
    // text over our dark background. These components own every colour and
    // font used by interactive controls so the visual language is stable on
    // Windows, Linux and a future CM5 desktop session.
    component GameButton: Button {
        id: gameButton
        property color accent: window.blue
        implicitHeight: 42
        hoverEnabled: true
        font.family: "Bahnschrift"
        font.pixelSize: 12
        font.bold: true
        contentItem: Text {
            text: gameButton.text
            color: gameButton.enabled ? "#f5fbff" : "#6d8294"
            font: gameButton.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 10
            border.width: 1
            border.color: gameButton.enabled ? Qt.lighter(gameButton.accent, gameButton.hovered ? 1.28 : 1.08) : "#25384b"
            color: !gameButton.enabled ? "#122031" : (gameButton.down ? Qt.darker(gameButton.accent, 1.38) : (gameButton.hovered ? Qt.lighter(gameButton.accent, 1.14) : gameButton.accent))
            Behavior on color { ColorAnimation { duration: 130 } }
            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 1; radius: 1; color: gameButton.enabled ? "#9eeeff" : "#34495c"; opacity: 0.55 }
        }
    }

    // A real Version/Author/Email/License info row, matching
    // HYDRA-UMC-UPDATER's own AboutInfoRow (HYDRA-UMC-STUDIO's own
    // About.tsx InfoRow before that).
    component AboutInfoRow: Rectangle {
        property string label: ""
        property string value: ""
        property color valueColor: window.textPrimary
        Layout.fillWidth: true
        implicitHeight: 34
        radius: 8
        color: "#07111e"
        border.width: 1
        border.color: window.border
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            LabelText { text: label.toUpperCase(); color: window.textMuted; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1 }
            Item { Layout.fillWidth: true }
            LabelText { text: value; color: valueColor; font.pixelSize: 11 }
        }
    }

    component GameCombo: ComboBox {
        id: gameCombo
        implicitHeight: 40
        font.family: "Bahnschrift"
        font.pixelSize: 12
        contentItem: Text {
            leftPadding: 13
            rightPadding: 34
            text: gameCombo.displayText
            color: "#edf7ff"
            font: gameCombo.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        indicator: Text {
            x: gameCombo.width - width - 13
            y: (gameCombo.height - height) / 2 - 1
            text: "⌄"
            color: window.cyan
            font.family: "Bahnschrift"
            font.pixelSize: 20
        }
        background: Rectangle {
            radius: 10
            color: gameCombo.pressed ? "#1a3954" : (gameCombo.hovered ? "#19334d" : "#12263a")
            border.width: 1
            border.color: gameCombo.hovered ? "#3dcce0" : "#315773"
            Behavior on color { ColorAnimation { duration: 120 } }
        }
        delegate: ItemDelegate {
            width: gameCombo.width
            height: 39
            contentItem: Text {
                text: modelData.label || modelData
                color: "#edf7ff"
                font.family: "Bahnschrift"
                font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
                leftPadding: 13
            }
            background: Rectangle { color: highlighted ? "#23516e" : "#10243a" }
        }
        popup: Popup {
            y: gameCombo.height + 5
            width: gameCombo.width
            implicitHeight: contentItem.implicitHeight
            padding: 1
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: gameCombo.popup.visible ? gameCombo.delegateModel : null
                currentIndex: gameCombo.highlightedIndex
            }
            background: Rectangle { radius: 10; color: "#10243a"; border.width: 1; border.color: "#3dcce0" }
        }
    }

    component GameCheck: CheckBox {
        id: gameCheck
        implicitHeight: 30
        hoverEnabled: true
        indicator: Rectangle {
            implicitWidth: 19
            implicitHeight: 19
            x: gameCheck.leftPadding
            y: parent.height / 2 - height / 2
            radius: 5
            color: gameCheck.checked ? window.cyan : "#10243a"
            border.width: 1
            border.color: gameCheck.hovered ? "#67e5f0" : "#42647c"
            Text { anchors.centerIn: parent; text: gameCheck.checked ? "✓" : ""; color: "#07111e"; font.pixelSize: 15; font.bold: true }
        }
        contentItem: Text {
            text: gameCheck.text
            color: gameCheck.enabled ? window.textMuted : "#5d7184"
            font.family: "Bahnschrift"
            font.pixelSize: 11
            leftPadding: gameCheck.indicator.width + 10
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.WordWrap
        }
    }

    // A real, styled text input - HYDRA-UMC-UPDATER's own Main.qml never
    // needed one (nothing there is free-text), but this repo's real
    // First-Boot Config form (hostname/user/password/Wi-Fi/timezone/
    // keyboard) and Build tab (output path) both do. Same panelAlt/
    // border/cyan-focus visual language as every other control here,
    // not a bare default QtQuick.Controls TextField.
    component GameField: TextField {
        id: gameField
        // Real user feedback: the placeholder text (and, since a TextField
        // shares one font for typed input and placeholder alike, the typed
        // text with it) read too small - font doubled from 12 to 24, but
        // the field box itself stays the original 38px tall (a follow-up
        // correction: the first pass also grew the box, which was
        // explicitly NOT wanted - bigger text, same-size field).
        implicitHeight: 38
        color: window.textPrimary
        font.family: "Bahnschrift"
        font.pixelSize: 24
        selectionColor: window.cyan
        placeholderTextColor: "#5d7184"
        leftPadding: 12
        rightPadding: 12
        background: Rectangle {
            radius: 9
            color: "#0d1c2c"
            border.width: 1
            border.color: gameField.activeFocus ? window.cyan : (gameField.hovered ? "#3a5a73" : window.border)
            Behavior on border.color { ColorAnimation { duration: 120 } }
        }
    }

    FileDialog {
        id: outputDialog
        title: ui("lbl_output_path")
        fileMode: FileDialog.SaveFile
        nameFilters: ["Disk image (*.img)"]
        onAccepted: outputPathField.text = selectedFile.toString().replace("file:///", "")
    }

    FileDialog {
        id: remoteKeyDialog
        title: ui("lbl_remote_key_path")
        fileMode: FileDialog.OpenFile
        onAccepted: remoteKeyPathField.text = selectedFile.toString().replace("file:///", "")
    }

    // First-Boot Config, moved into its own dialog (used to be a 3rd tab) -
    // opened from a button next to Build Image, since building a real image
    // is naturally the action this config feeds into (buildImage() below
    // reads these same field ids directly, dialog or not - QML id scoping
    // is document-wide, not limited to this Dialog's own visual subtree).
    Dialog {
        id: firstBootDialog
        modal: true
        anchors.centerIn: parent
        width: 460
        padding: 22
        background: Rectangle { color: window.panel; radius: 16; border.color: window.border; border.width: 1 }
        contentItem: ColumnLayout {
            spacing: 12
            LabelText { text: ui("dlg_first_boot_title"); font.pixelSize: 16; font.bold: true }
            GridLayout {
                columns: 2
                columnSpacing: 16
                rowSpacing: 10
                Layout.fillWidth: true
                LabelText { text: ui("lbl_hostname"); color: window.textMuted }
                GameField { id: hostnameField; Layout.fillWidth: true }
                LabelText { text: ui("lbl_username"); color: window.textMuted }
                GameField { id: usernameField; Layout.fillWidth: true }
                LabelText { text: ui("lbl_password"); color: window.textMuted }
                GameField { id: passwordField; echoMode: TextInput.Password; Layout.fillWidth: true }
                LabelText { text: ui("lbl_wifi_ssid"); color: window.textMuted }
                GameField { id: wifiSsidField; Layout.fillWidth: true }
                LabelText { text: ui("lbl_wifi_password"); color: window.textMuted }
                GameField { id: wifiPasswordField; echoMode: TextInput.Password; Layout.fillWidth: true }
                LabelText { text: ui("lbl_wifi_country"); color: window.textMuted }
                GameField { id: wifiCountryField; text: "US"; Layout.preferredWidth: 90 }
                LabelText { text: ui("lbl_timezone"); color: window.textMuted }
                GameField { id: timezoneField; placeholderText: "Europe/Madrid"; Layout.fillWidth: true }
                LabelText { text: ui("lbl_keyboard"); color: window.textMuted }
                GameField { id: keyboardField; placeholderText: "us"; Layout.preferredWidth: 90 }
            }
            GameCheck { id: sshCheck; text: ui("lbl_enable_ssh"); checked: true }
            LabelText {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                font.pixelSize: 10
                color: window.textMuted
                text: ui("lbl_firstboot_dialog_hint")
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border }
            RowLayout {
                spacing: 8
                Layout.fillWidth: true
                GameField { id: configOutField; Layout.fillWidth: true; placeholderText: "boot/" }
                GameButton {
                    text: ui("btn_save_config")
                    accent: "#264966"
                    onClicked: {
                        var result = backend.saveFirstBootConfig(
                            configOutField.text, hostnameField.text, usernameField.text, passwordField.text,
                            sshCheck.checked, wifiSsidField.text, wifiPasswordField.text, wifiCountryField.text,
                            timezoneField.text, keyboardField.text, ""
                        )
                        statusLabel.text = result
                        statusLabel.color = result.indexOf("error") === 0 ? window.red : window.green
                    }
                }
            }
            LabelText { id: statusLabel; color: window.textMuted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                GameButton { text: ui("about_close_button"); accent: window.cyan; onClicked: firstBootDialog.close() }
            }
        }
    }

    Dialog {
        id: aboutDialog
        modal: true
        anchors.centerIn: parent
        width: 440
        padding: 24
        background: Rectangle { color: window.panel; radius: 16; border.color: window.border; border.width: 1 }
        contentItem: ColumnLayout {
            spacing: 8

            // Real animated mark, same source and renderer as the main
            // header above - not a placeholder "H" box.
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Rectangle {
                    Layout.preferredWidth: 88; Layout.preferredHeight: 88; radius: 20
                    color: "#0e3045"; border.width: 1; border.color: "#2d7695"
                    VectorImage {
                        anchors.fill: parent; anchors.margins: 10
                        source: "../../../images/HYDRA_UMC_ICON.svg"
                        preferredRendererType: VectorImage.CurveRenderer
                        animations.loops: Animation.Infinite
                        animations.paused: false
                    }
                }
                Item { Layout.fillWidth: true }
            }

            LabelText {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: "HYDRA<font color=\"" + window.green + "\">-UM</font><font color=\"" + window.red + "\">C</font> <font color=\"" + window.cyan + "\">OS REBUILDER</font>"
                textFormat: Text.RichText
                font.pixelSize: 18
                font.bold: true
                font.letterSpacing: 1
            }
            LabelText {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: ui("about_tagline")
                color: window.cyan
                font.pixelSize: 12
                font.bold: true
            }
            LabelText {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: ui("about_description")
                color: window.textMuted
                font.pixelSize: 11
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.topMargin: 6
                spacing: 4
                AboutInfoRow { label: ui("about_version_label"); value: backend.appVersion }
                AboutInfoRow { label: ui("about_author_label"); value: "JuanenRac (Electro Hobby 3D)" }
                AboutInfoRow {
                    label: ui("about_email_label")
                    valueColor: window.cyan
                    value: "electrohobby3d@gmail.com"
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: Qt.openUrlExternally("mailto:electrohobby3d@gmail.com") }
                }
                AboutInfoRow { label: ui("about_license_label"); value: ui("about_license") }
            }

            RowLayout { Layout.fillWidth: true; Layout.topMargin: 8
                GameButton { text: ui("open_github_button"); Layout.preferredWidth: 223; accent: "#264966"; onClicked: Qt.openUrlExternally("https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER") }
                Item { Layout.fillWidth: true }
                GameButton { text: ui("about_close_button"); Layout.preferredWidth: 140; accent: window.cyan; onClicked: aboutDialog.close() }
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0a1a2b" }
            GradientStop { position: 0.46; color: "#07111e" }
            GradientStop { position: 1.0; color: "#06101a" }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 28
        anchors.rightMargin: 28
        anchors.topMargin: 22
        anchors.bottomMargin: 18
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 78
            spacing: 16
            Rectangle {
                width: 54; height: 54; radius: 16
                color: "#0e3045"; border.width: 1; border.color: "#2d7695"
                // Image rasterizes SVG into one image for this surface.
                // VectorImage preserves the official SVG's supported SMIL
                // transform animation, so the mark remains alive instead
                // of becoming a static logo in the command header.
                VectorImage {
                    anchors.fill: parent
                    anchors.margins: 5
                    source: "../../../images/HYDRA_UMC_ICON.svg"
                    preferredRendererType: VectorImage.CurveRenderer
                    animations.loops: Animation.Infinite
                    animations.paused: false
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                LabelText { text: "HYDRA-UMC"; color: window.cyan; font.pixelSize: 13; font.bold: true; font.letterSpacing: 1.2 }
                LabelText { text: "OS REBUILDER"; font.pixelSize: 25; font.bold: true; font.letterSpacing: 1.1 }
                LabelText { text: ui("ui_subtitle"); color: window.textMuted; font.pixelSize: 13 }
            }
            Rectangle {
                color: "#10283a"; radius: 13; border.color: "#21516a"; border.width: 1
                Layout.preferredWidth: 160; Layout.preferredHeight: 48
                Row { anchors.centerIn: parent; spacing: 9
                    Rectangle { width: 9; height: 9; radius: 5; color: (backend.busy || backend.buildBusy) ? window.amber : window.green
                        SequentialAnimation on opacity {
                            running: backend.busy || backend.buildBusy
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.32; duration: 620 }
                            NumberAnimation { to: 1; duration: 620 }
                        }
                    }
                    LabelText { text: (backend.busy || backend.buildBusy) ? ui("status_busy") : ui("status_online"); color: window.textMuted; font.pixelSize: 11; font.bold: true }
                }
            }
            GameCombo {
                id: languageCombo
                Layout.preferredWidth: 145
                model: backend.availableLanguages
                textRole: "label"
                Component.onCompleted: {
                    for (var i = 0; i < model.length; ++i) if (model[i].code === backend.language) currentIndex = i
                }
                onActivated: backend.setLanguage(model[currentIndex].code)
            }
            GameButton { text: ui("menu_about"); Layout.preferredWidth: 140; accent: "#264966"; onClicked: aboutDialog.open() }
        }

        // Real, draggable dividers between the 3 columns below - user
        // feedback: "que se puedan mover de izquierda a derecha para yo
        // elegir si el de build log lo quiero mas grande". Each handle is
        // restyled to match this window's own dark theme (Qt's default
        // SplitView handle renders as a plain native-grey bar otherwise,
        // clashing with everything around it).
        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            handle: Rectangle {
                implicitWidth: 14
                color: "transparent"
                Rectangle {
                    anchors.centerIn: parent
                    width: 3; height: parent.height * 0.5
                    radius: 2
                    color: SplitHandle.pressed ? window.cyan : (SplitHandle.hovered ? "#3a5a73" : window.border)
                    Behavior on color { ColorAnimation { duration: 120 } }
                }
            }

            // -- Ecosystem Status - the real project list, always visible,
            // no longer hidden behind a tab. -----------------------------
            SectionPanel {
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.minimumWidth: 320
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        LabelText { text: ui("tab_status"); font.pixelSize: 16; font.bold: true }
                        LabelText { text: backend.status; color: window.textMuted; Layout.fillWidth: true }
                        MetricCard { Layout.preferredWidth: 170; caption: ui("col_project"); value: String(backend.projectCount); accent: window.cyan }
                        GameButton { text: ui("btn_refresh"); Layout.preferredWidth: 298; enabled: !backend.busy; accent: window.cyan; onClicked: backend.refresh() }
                    }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 31; color: "#172a40"; radius: 7
                        RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 8
                            LabelText { text: ui("col_project"); color: window.textMuted; font.pixelSize: 10; font.bold: true; Layout.fillWidth: true }
                            LabelText { text: ui("col_version"); color: window.textMuted; font.pixelSize: 10; font.bold: true; Layout.preferredWidth: 100; horizontalAlignment: Text.AlignHCenter }
                            LabelText { text: ui("col_role"); color: window.textMuted; font.pixelSize: 10; font.bold: true; Layout.preferredWidth: 110; horizontalAlignment: Text.AlignHCenter }
                            LabelText { text: ui("col_stack"); color: window.textMuted; font.pixelSize: 10; font.bold: true; Layout.preferredWidth: 110; horizontalAlignment: Text.AlignHCenter }
                        }
                    }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: backend.projects
                        ScrollBar.vertical: ScrollBar { }
                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width; height: 44; radius: 8
                            color: rowArea.containsMouse ? "#172c43" : "#112238"
                            Behavior on color { ColorAnimation { duration: 130 } }
                            MouseArea { id: rowArea; anchors.fill: parent; hoverEnabled: true }
                            RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12; spacing: 8
                                LabelText { text: "◆  " + modelData.name; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                                LabelText { text: modelData.version; color: window.green; font.pixelSize: 11; font.bold: true; Layout.preferredWidth: 100; horizontalAlignment: Text.AlignHCenter }
                                LabelText { text: modelData.role; color: window.textMuted; font.pixelSize: 10; Layout.preferredWidth: 110; horizontalAlignment: Text.AlignHCenter }
                                LabelText { text: modelData.stack; color: window.textMuted; font.pixelSize: 10; Layout.preferredWidth: 110; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight }
                            }
                        }
                    }
                }
            }

            // -- Build Image - to the right of the list, as requested,
            // with First-Boot Config now a button that opens its own
            // dialog (defined above, near outputDialog) rather than a
            // 3rd tab - matches HYDRA-UMC-UPDATER's own narrow right-side
            // action panel. Real Build Target choice: this same machine
            // (only possible when backend.platformOk - Linux+root) or a
            // real remote host over SSH (buildImageRemote in qt_gui.py) -
            // the only way to get a real build done from Windows, which
            // can never itself pass check_build_platform().
            SectionPanel {
                // Real user feedback: take 25% of Ecosystem Status's own
                // width (measured live at a real 1920px window: 1196px,
                // so ~300px) and give it to this column and Build Log
                // below in equal halves (+150 each) - was 340.
                SplitView.preferredWidth: 490
                SplitView.minimumWidth: 280
                SplitView.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        LabelText { text: ui("tab_build"); font.pixelSize: 16; font.bold: true; Layout.fillWidth: true }
                        GameButton { text: ui("btn_first_boot_config"); Layout.preferredWidth: 339; accent: "#264966"; onClicked: firstBootDialog.open() }
                    }

                    LabelText { text: ui("lbl_build_target"); color: window.textMuted; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1 }
                    Rectangle {
                        // Real user feedback: both build-target buttons on
                        // one line, inside their own frame.
                        Layout.fillWidth: true
                        implicitHeight: buildTargetRow.implicitHeight + 16
                        radius: 10
                        color: window.panelAlt
                        border.width: 1
                        border.color: window.border
                        RowLayout {
                            id: buildTargetRow
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 6
                            GameButton { text: ui("build_target_local"); Layout.fillWidth: true; accent: window.buildTarget === "local" ? window.cyan : "#1a3040"; onClicked: window.buildTarget = "local" }
                            GameButton { text: ui("build_target_remote"); Layout.fillWidth: true; accent: window.buildTarget === "remote" ? window.cyan : "#1a3040"; onClicked: window.buildTarget = "remote" }
                        }
                    }

                    // -- Local target: the real platform gate, honest either way.
                    Rectangle {
                        visible: window.buildTarget === "local"
                        Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; radius: 9
                        implicitHeight: platformLabel.implicitHeight + 20
                        color: backend.platformOk ? Qt.rgba(window.green.r, window.green.g, window.green.b, 0.12) : Qt.rgba(window.amber.r, window.amber.g, window.amber.b, 0.12)
                        border.width: 1; border.color: backend.platformOk ? window.green : window.amber
                        LabelText { id: platformLabel; anchors.fill: parent; anchors.margins: 10; verticalAlignment: Text.AlignVCenter; wrapMode: Text.WordWrap; text: backend.platformOk ? ui("lbl_platform_ready") : (ui("lbl_platform_blocked") + " " + backend.platformReason); color: backend.platformOk ? window.green : window.amber; font.pixelSize: 11 }
                    }

                    // -- Remote target: a real SSH connection this machine
                    // dispatches the actual Linux+root build to (see
                    // qt_gui.py's own _start_remote_build).
                    ColumnLayout {
                        visible: window.buildTarget === "remote"
                        Layout.fillWidth: true
                        spacing: 8
                        Rectangle {
                            // Real user feedback: both remote-preset buttons
                            // inside their own frame (already on one line).
                            Layout.fillWidth: true
                            implicitHeight: remotePresetRow.implicitHeight + 16
                            radius: 10
                            color: window.panelAlt
                            border.width: 1
                            border.color: window.border
                            RowLayout {
                                id: remotePresetRow
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 6
                                GameButton {
                                    text: ui("remote_preset_cm5"); Layout.fillWidth: true
                                    accent: window.remotePreset === "cm5" ? window.cyan : "#1a3040"
                                    onClicked: { window.remotePreset = "cm5"; remoteHostField.text = "192.168.0.180"; remoteUsernameField.text = "hydra-umc"; window.remoteAuthMethod = "key" }
                                }
                                GameButton {
                                    text: ui("remote_preset_custom"); Layout.fillWidth: true
                                    accent: window.remotePreset === "custom" ? window.cyan : "#1a3040"
                                    onClicked: window.remotePreset = "custom"
                                }
                            }
                        }
                        Rectangle {
                            visible: window.remotePreset === "cm5"
                            Layout.fillWidth: true; implicitHeight: cm5WarnLabel.implicitHeight + 16; radius: 8
                            color: Qt.rgba(window.amber.r, window.amber.g, window.amber.b, 0.12)
                            border.width: 1; border.color: window.amber
                            LabelText { id: cm5WarnLabel; anchors.fill: parent; anchors.margins: 8; wrapMode: Text.WordWrap; text: ui("lbl_remote_cm5_warning"); color: window.amber; font.pixelSize: 10 }
                        }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 6
                            GameField { id: remoteHostField; Layout.fillWidth: true; placeholderText: ui("lbl_remote_host"); Component.onCompleted: if (window.remotePreset === "cm5") text = "192.168.0.180" }
                            GameField { id: remotePortField; Layout.preferredWidth: 60; text: "22" }
                        }
                        GameField { id: remoteUsernameField; Layout.fillWidth: true; placeholderText: ui("lbl_remote_username"); Component.onCompleted: if (window.remotePreset === "cm5") text = "hydra-umc" }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            GameButton { text: ui("remote_auth_key"); Layout.fillWidth: true; accent: window.remoteAuthMethod === "key" ? window.blue : "#1a3040"; onClicked: window.remoteAuthMethod = "key" }
                            GameButton { text: ui("remote_auth_password"); Layout.fillWidth: true; accent: window.remoteAuthMethod === "password" ? window.blue : "#1a3040"; onClicked: window.remoteAuthMethod = "password" }
                        }
                        ColumnLayout {
                            visible: window.remoteAuthMethod === "key"
                            Layout.fillWidth: true
                            spacing: 8
                            RowLayout {
                                Layout.fillWidth: true; spacing: 6
                                GameField { id: remoteKeyPathField; Layout.fillWidth: true; placeholderText: ui("lbl_remote_key_path") }
                                GameButton { text: ui("browse_button"); accent: "#265c89"; onClicked: remoteKeyDialog.open() }
                            }
                            GameField { id: remoteKeyPassphraseField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: ui("lbl_remote_key_passphrase") }
                        }
                        GameField { id: remotePasswordField; visible: window.remoteAuthMethod === "password"; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: ui("lbl_remote_password") }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        GameField { id: outputPathField; Layout.fillWidth: true; placeholderText: "hydra-umc-cm5.img" }
                        GameButton { text: ui("browse_button"); accent: "#265c89"; onClicked: outputDialog.open() }
                    }
                    GameButton {
                        text: ui("btn_build")
                        Layout.fillWidth: true
                        accent: window.green
                        enabled: !backend.buildBusy && (window.buildTarget === "local" ? backend.platformOk : (remoteHostField.text.length > 0 && remoteUsernameField.text.length > 0))
                        onClicked: {
                            var opts = {
                                target: window.buildTarget,
                                outputPath: outputPathField.text,
                                hostname: hostnameField.text, fbUsername: usernameField.text, fbPassword: passwordField.text,
                                enableSsh: sshCheck.checked, wifiSsid: wifiSsidField.text, wifiPassword: wifiPasswordField.text,
                                wifiCountry: wifiCountryField.text, timezone: timezoneField.text, keyboard: keyboardField.text
                            }
                            if (window.buildTarget === "remote") {
                                opts.host = remoteHostField.text
                                opts.port = remotePortField.text
                                opts.username = remoteUsernameField.text
                                opts.authMethod = window.remoteAuthMethod
                                opts.password = remotePasswordField.text
                                opts.keyPath = remoteKeyPathField.text
                                opts.keyPassphrase = remoteKeyPassphraseField.text
                            }
                            backend.buildImage(opts)
                        }
                    }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: window.border }
                    // Real checkpoint list, one phase per row - same visual
                    // language as HYDRA-UMC-UPDATER's own Safe Update panel
                    // (a filled circle with ✓/!/›, a label next to it),
                    // stacked instead of wrapped in a Flow per real user
                    // feedback ("ponlos uno debajo de otro").
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 7
                        Repeater {
                            model: window.buildPhases
                            delegate: RowLayout {
                                required property string modelData
                                property string state: window.checkpointState(modelData)
                                Layout.fillWidth: true; spacing: 8
                                Rectangle {
                                    Layout.preferredWidth: 15; Layout.preferredHeight: 15; radius: 8
                                    color: window.checkpointColor(state)
                                    border.width: 1; border.color: Qt.lighter(window.checkpointColor(state), 1.2)
                                    LabelText { anchors.centerIn: parent; text: state === "done" ? "✓" : (state === "active" ? "›" : ""); color: "#07111e"; font.pixelSize: 10; font.bold: true }
                                }
                                // Real, translated, descriptive label per
                                // real user feedback ("textos más amplios")
                                // - was the raw, untranslated phase key
                                // (e.g. "firstboot-config") before.
                                LabelText { text: ui("checkpoint_" + modelData.replace(/-/g, "_")); color: state === "pending" ? window.textMuted : window.textPrimary; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            }
                        }
                    }
                    LabelText { visible: backend.buildBusy; text: backend.buildDetail; color: window.textMuted; font.pixelSize: 10; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Item { Layout.fillHeight: true }
                }
            }

            // -- Build Log - its own column to the right, per real user
            // feedback (previously crammed under the Build Image controls).
            SectionPanel {
                // Same real 25%-of-Ecosystem-Status redistribution as
                // the Build Image column above (+150 each) - was 300.
                SplitView.preferredWidth: 450
                SplitView.minimumWidth: 200
                SplitView.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        LabelText { text: ui("activity_log_title"); font.pixelSize: 16; font.bold: true; Layout.fillWidth: true }
                        GameButton {
                            text: ui("btn_copy_log")
                            Layout.preferredWidth: 116
                            accent: "#264966"
                            onClicked: {
                                buildLogArea.selectAll()
                                buildLogArea.copy()
                                buildLogArea.deselect()
                            }
                        }
                    }
                    // A real, selectable/copyable log - real user feedback:
                    // the previous ListView-of-Text rendering couldn't be
                    // selected or copy-pasted at all, so a real failure's
                    // own error text had no way out of the window. A
                    // TextArea inside a ScrollView gives real text
                    // selection, Ctrl+C, and a real scrollbar together.
                    // backend.buildLog is also mirrored to a real log FILE
                    // on disk (see qt_gui.py's own LOGS_DIR) for when
                    // copy-paste still isn't convenient enough (e.g.
                    // reporting a bug to someone else).
                    Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; color: "#081623"; radius: 9; border.width: 1; border.color: "#1d4056"
                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: 10
                            clip: true
                            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                            TextArea {
                                id: buildLogArea
                                text: backend.buildLog.map(function(line) { return "› " + line }).join("\n")
                                readOnly: true
                                selectByMouse: true
                                wrapMode: TextArea.Wrap
                                color: "#9adce3"
                                selectionColor: window.cyan
                                font.family: "Cascadia Mono"
                                font.pixelSize: 10
                                background: null
                                // Keeps the view pinned to the newest line as
                                // the real build streams in - a fixed 0
                                // would leave the reader stuck at the first
                                // line while a multi-minute build fills the
                                // box far past what's visible.
                                onTextChanged: cursorPosition = length
                            }
                        }
                    }
                    LabelText { text: ui("lbl_log_file_prefix") + " " + backend.logFilePath; color: window.textMuted; font.pixelSize: 9; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true; elide: Text.ElideMiddle }

                    // Real progress bar, per real user feedback ("falta una
                    // barra de progreso... debajo de la ventana de logs
                    // aunque la ventana de logs pierda longitud vertical") -
                    // deliberately placed below the log so the log Rectangle
                    // above (Layout.fillHeight: true) is the one that yields
                    // height to it, not the other way round. Same honest,
                    // discrete-phase math as checkpointState() above (real
                    // position in window.buildPhases), never a smoothly
                    // animated fake percentage - the Behavior below only
                    // animates the WIDGET's transition between two real,
                    // known milestones.
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        RowLayout {
                            Layout.fillWidth: true
                            // Real user feedback: double the size of the
                            // texts next to the progress bar (9 -> 18).
                            LabelText {
                                text: backend.buildBusy || backend.buildPhase !== "" ? backend.buildPhase : ui("lbl_build_progress_idle")
                                color: window.textMuted; font.pixelSize: 18; Layout.fillWidth: true
                            }
                            LabelText {
                                text: Math.round(window.buildProgressFraction * 100) + "%"
                                color: window.cyan; font.pixelSize: 18; font.bold: true
                            }
                        }
                        Rectangle {
                            // Real user feedback: double the progress bar's
                            // own height (8 -> 16).
                            Layout.fillWidth: true; Layout.preferredHeight: 16; radius: 8
                            color: "#081623"; border.width: 1; border.color: "#1d4056"
                            Rectangle {
                                anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
                                anchors.margins: 1; radius: 7
                                width: Math.max(0, (parent.width - 2) * window.buildProgressFraction)
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0.0; color: window.blue }
                                    GradientStop { position: 1.0; color: window.cyan }
                                }
                                Behavior on width { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                            }
                        }
                    }
}
            }
        }

        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 35; radius: 8; color: "#091827"; border.width: 1; border.color: "#17354a"
            RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 12
                LabelText { text: "v" + backend.appVersion; color: window.cyan; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1 }
                LabelText { text: backend.status; color: window.textMuted; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                BusyIndicator { running: backend.busy || backend.buildBusy; visible: running; Layout.preferredWidth: 22; Layout.preferredHeight: 22 }
            }
        }
    }

    Component.onCompleted: backend.refresh()
}
