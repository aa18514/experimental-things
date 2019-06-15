/* eslint-disable */
var ace, userEditor, solnEditor, jsEditor;
var activeCanvasId='userCanvas';
var shellHistory = [ '' ], shellHistoryIndex = 0;

function compilePyToJs(pyCode) {
    try {
        return py2js(pyCode);
    }
    catch (e) {
        window.alert('compilePyToJs: Error: ' + e);
        return '"Error"';
    }
}

function postToIDE(type, eventDetail) {
    eventDetail.canvasId = activeCanvasId;
    var ideEvent = new CustomEvent(type, { detail : eventDetail });
    document.getElementById('brython-target').dispatchEvent(ideEvent);
}

function onUserCanvasButton() {
    activeCanvasId = 'userCanvas';
    document.getElementById('userCanvasDiv').style.visibility = 'visible';
    document.getElementById('solnCanvasDiv').style.visibility = 'hidden';
}

function onSolnCanvasButton() {
    activeCanvasId = 'solnCanvas';
    document.getElementById('solnCanvasDiv').style.visibility = 'visible';
    document.getElementById('userCanvasDiv').style.visibility = 'hidden';
}

function onDocsButton() {
    window.open('docs-dev.html', '_blank');
}

function onMouseMove(event) {
    var rect = document.getElementById('userCanvas').getBoundingClientRect();
    var x = Math.round(event.clientX - rect.left);
    var y = Math.round(event.clientY - rect.top);
    document.getElementById('canvasInfoDiv').innerHTML = ('(' + x + ',' + y + ')');
}

function onRunStopButton() {
    var agContainer = document.getElementById('agFeedbackContainer');
    agContainer.style.visibility = 'hidden';
    var label = document.getElementById('runStopButton').innerHTML;
    if (label === 'run') onRunButton(false, false);
    else onStopButton();
}

function setRunningButtonsEnabled(enabled) {
    var labels = ['pauseButton', 'stepButton'];
    for (var i=0; i<labels.length; i++) {
        var button = labels[i];
        document.getElementById(button).disabled = !enabled
    }
}

function onGetJsButton() {
    var userCode = userEditor.getValue();
    var jsCode = compilePyToJs(userCode);
    window.localStorage.setItem('_cmu_cs_academy_dev_ide_jsCode_', jsCode);
    jsEditor.setValue(jsCode);
}

function onRunJsButton() {
    onRunButton(true, false);
}

function onRunTestCaseButton() {
    onRunButton(false, true);
}

function onRunSolnButton() {
    var solnCode = solnEditor.getValue();
    onSolnCanvasButton();
    postToIDE('brythonRunCode', {
        snippets : [ { code : solnCode, mode : 'py' } ],
        resetGlobals : true
    });
}

function onRunButton(jsMode, testCaseMode) {
    onUserCanvasButton();
    document.getElementById('runStopButton').innerHTML = 'stop';
    document.getElementById('output').value = '';
    // save file
    try {
        var userCode = userEditor.getValue();
        window.localStorage.setItem('_cmu_cs_academy_dev_ide_userCode_', userCode);
        var solnCode = solnEditor.getValue();
        window.localStorage.setItem('_cmu_cs_academy_dev_ide_solnCode_', solnCode);
        var jsCode = jsEditor.getValue();
        window.localStorage.setItem('_cmu_cs_academy_dev_ide_jsCode_', jsCode);
        var testCaseCode = testCaseEditor.getValue();
        window.localStorage.setItem('_cmu_cs_academy_dev_ide_testCaseCode_', testCaseCode);
    }
    catch (e) {
    }
    var snippets = [{ code: jsMode ? jsCode : userCode, mode: jsMode ? 'js' : 'py'}];
    if (testCaseMode) snippets.push({ code:testCaseCode, mode:'py'});
    postToIDE('brythonRunCode', {
        snippets : snippets,
        resetGlobals : true
    });
    setRunningButtonsEnabled(true);
}

var agId = 0;
var agTime0 = 0;

var agSeed = 1234;

var bulkAgUserCodes = null;

function nextBulkAgUserCode() {
    if ((bulkAgUserCodes === null) || (bulkAgUserCodes.length === 0)) { return null; }
    var code = '';
    while (bulkAgUserCodes.length !== 0) {
        code = bulkAgUserCodes.shift().trim();
        if (code.length > 0) break;
    }
    if (bulkAgUserCodes.length === 0) { bulkAgUserCodes = null; }
    code = '# ' + code;
    // window.alert(code);
    userEditor.setValue(code);
}

function onStopButton() {
    document.getElementById('runStopButton').innerHTML = 'run';
    postToIDE('brythonStop', { });
    setRunningButtonsEnabled(false);
}

function onPauseButton() {
    var label = document.getElementById('pauseButton').innerHTML;
    if (label === 'pause') postToIDE('brythonPause', { });
    else postToIDE('brythonUnpause', { });
}

function onStepButton() { postToIDE('brythonStep', { }); }

function onKeyPressInShellInput(event) {
    if (event.keyCode == 13) {
        var cmd = document.getElementById('shellInput').value;
        shellHistory.push(cmd);
        shellHistoryIndex = 0;
        document.getElementById('shellInput').value = '';
        postToIDE('brythonShellInput', { input : cmd });
    }
}

function onKeyDownInShellInput(event) {
    var up = (event.keyCode === 38), down = (event.keyCode === 40);
    if (up || down) {
        if (down) {
            shellHistoryIndex += 1;
            if (shellHistoryIndex >= shellHistory.length) shellHistoryIndex = 0;
        }
        else {
            shellHistoryIndex -= 1;
            if (shellHistoryIndex < 0) shellHistoryIndex = shellHistory.length - 1;
        }
        document.getElementById('shellInput').value = shellHistory[shellHistoryIndex];
        event.preventDefault();
    }
}

function setInspectorInfoMsg(event) {
    var imContainer = document.getElementById('imFeedbackContainer');
    var imFeedback = document.getElementById('imFeedback');
    imContainer.style.visibility = 'visible';
    imFeedback.innerHTML = event.detail.msg;
}

function clearInspectorInfoMsg() {
    var imContainer = document.getElementById('imFeedbackContainer');
    var imFeedback = document.getElementById('imFeedback');
    imContainer.style.visibility = 'hidden';
}

function nextAgError() { if (agDetail) setAgError(agDetail.i + 1); }
function prevAgError() { if (agDetail) setAgError(agDetail.i - 1); }

function setUserCode(userCode) {
    if (userCode) {
        userEditor.setValue(userCode);
        window.localStorage.setItem('_cmu_cs_academy_dev_ide_userCode_', userCode);
        var lines = userCode.split('\n').length;
        userEditor.scrollToLine(lines, true, true, function(){ });
        userEditor.clearSelection();
    }
}

function onTestCaseCompleted(event) {
    setUserCode(event.detail.userCode);
    frameworkStop(event);
    printOutput('Test Case Completed\n');
}

function printOutput(s) {
    var textarea = document.getElementById('output');
    textarea.value += s;
    textarea.scrollTop = textarea.scrollHeight;
}

function frameworkPrintLine(event) {
    printOutput(event.detail.line);
}

function frameworkStop(event) {
    document.getElementById('runStopButton').innerHTML = 'run';
    setRunningButtonsEnabled(false);
}

function frameworkPause(event) {
    document.getElementById('pauseButton').innerHTML = 'unpause';
}

function frameworkUnpause(event) {
    document.getElementById('pauseButton').innerHTML = 'pause';
}

function setupEditor(divId) {
    var editor = ace.edit(divId);
    editor.enableCopyPaste = true;
    editor.privateClipboard = "Carpe diem!";
    editor.getSession().setMode("ace/mode/python");
    editor.setTheme("ace/theme/xcode");
    editor.setShowPrintMargin(true);
    editor.setHighlightActiveLine(true);
    editor.setFontSize(12);
    editor.$blockScrolling = Infinity;
    editor.getSession().on('change', function() {
        var agContainer = document.getElementById('agFeedbackContainer');
        var agFeedback = document.getElementById('agFeedback');
        agContainer.style.background= 'grey';
        agFeedback.innerHTML = '';
    });
    return editor;
}

function setupAppTargetEvents() {
    // setup events
    var appTarget = document.getElementById('application-target');
    appTarget.addEventListener('frameworkPrintLine', frameworkPrintLine);
    appTarget.addEventListener('frameworkStop', frameworkStop);
    appTarget.addEventListener('frameworkPause', frameworkPause);
    appTarget.addEventListener('frameworkUnpause', frameworkUnpause);
    appTarget.addEventListener('onTestCaseCompleted', onTestCaseCompleted);
    appTarget.addEventListener('setInspectorInfoMsg', setInspectorInfoMsg);
    appTarget.addEventListener('clearInspectorInfoMsg', clearInspectorInfoMsg);
}

function setupCanvasEvents() {
  var canvasElem = document.getElementById('userCanvas')
  document.addEventListener("keydown", function (e) {
    if (e.path.indexOf(canvasElem) == -1) {
      canvasElem.dispatchEvent(new e.constructor(e.type, e));
      e.preventDefault();
      e.stopPropagation();
    }
  });
  document.addEventListener("keyup", function (e) {
    if (e.path.indexOf(canvasElem) == -1) {
      canvasElem.dispatchEvent(new e.constructor(e.type, e));
      e.preventDefault();
      e.stopPropagation();
    }
  });
}

function setupEditorAndTerminal() {
    ace.require("ace/ext/language_tools");
    userEditor = setupEditor("userCodeEditorDiv");
    solnEditor = setupEditor("solnCodeEditorDiv");
    solnEditor.container.style.background="lightblue";
    testCaseEditor = setupEditor("testCaseCodeEditorDiv");
    testCaseEditor.container.style.background="pink";
    jsEditor = setupEditor("jsCodeEditorDiv");
    jsEditor.container.style.background="sandybrown";

    window.onblur = function() { postToIDE('brythonPause', { } ); };

    document.getElementById('userCanvasButton').addEventListener("click", onUserCanvasButton);
    document.getElementById('solnCanvasButton').addEventListener("click", onSolnCanvasButton);
    document.getElementById('docsButton').addEventListener("click", onDocsButton);
    document.getElementById('runStopButton').addEventListener("click", onRunStopButton);
    document.getElementById('runTestCaseButton').addEventListener("click", onRunTestCaseButton);

    document.getElementById('runJsButton').addEventListener("click", onRunJsButton);
    document.getElementById('getJsButton').addEventListener("click", onGetJsButton);
    document.getElementById('runSolnButton').addEventListener("click", onRunSolnButton);
    document.getElementById('agWithTestCaseButton').addEventListener("click", onAgWithTestCaseButton);
    document.getElementById('agNextButton').addEventListener("click", nextAgError);
    document.getElementById('agPrevButton').addEventListener("click", prevAgError);
    document.getElementById('pauseButton').addEventListener("click", onPauseButton);
    document.getElementById('stepButton').addEventListener("click", onStepButton);

    document.getElementById('shellInput').addEventListener('keypress', onKeyPressInShellInput)
    document.getElementById('shellInput').addEventListener('keydown', onKeyDownInShellInput)
    document.getElementById('userCanvas').addEventListener("mousemove", onMouseMove);

    setupAppTargetEvents();

    // preload editor
    try {
        var userCode = window.localStorage.getItem('_cmu_cs_academy_dev_ide_userCode_');
        userEditor.setValue(userCode, 1);
        var solnCode = window.localStorage.getItem('_cmu_cs_academy_dev_ide_solnCode_');
        solnEditor.setValue(solnCode, 1);
        var testCaseCode = window.localStorage.getItem('_cmu_cs_academy_dev_ide_testCaseCode_');
        testCaseEditor.setValue(testCaseCode, 1);
        var jsCode = window.localStorage.getItem('_cmu_cs_academy_dev_ide_jsCode_');
        jsEditor.setValue(jsCode, 1);
    }
    catch (e) {
    }
}
