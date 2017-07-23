//  1. Define sheet names where data is to be written below
var SHEET_NAME = "Influence";

//  2. Go to Tools > Script Editor
//
//  3. Run > setup
//
//  4. Publish > Deploy as web app 
//    - enter Project Version name and click 'Save New Version' 
//    - set security level and enable service (execute as 'me' and access 'anyone, even anonymously')
//
//  5. Copy the 'Current web app URL' and post this in your form/script action 
//
//  6. Insert column names on your destination sheet matching the parameter names of the data you are passing in (exactly matching case)

// Property Service used to store Sheet ID and API Key
var SCRIPT_PROP = PropertiesService.getScriptProperties();
// Property that defines whether duplicates are checked for
var PROPERTY_DUPS = "dups_ignore"; // set to other than "yes" to allow duplicates
// Property that defines the headers to skip in duplicate check
var PROPERTY_DUPS_SKIP = "dups_skip"; // comma-separated header list
// Recommend setting to "EventDate,EventTime" for Influence sheet.
var DUPS_SKIP_DEFAULT = ["EventDate","EventTime"];
 
// Expose POST method only
function doPost(e){
  return handleResponse(e);
}

// Update the sheet with the values provided in the request
function updateSheet(doc, e) {
  // store values in the appropriate sheet
  var sheet = doc.getSheetByName(SHEET_NAME);

  // we'll use headers in row 1 to define attributes to retrieve
  var lastColumn = sheet.getLastColumn();
  var headers = sheet.getRange(1, 1, 1, lastColumn).getValues()[0];
  var lastRowIdx = sheet.getLastRow();
  var nextRowIdx = lastRowIdx+1; // define next row offset
  var row = [];
  // loop through the header columns, ignoring undefined entries
  for (header in headers) {
    if (typeof e.parameter[headers[header]] != "undefined") {
      row.push(e.parameter[headers[header]]);
    }
  }
    
  if (!isDuplicate(sheet, headers, lastRowIdx, lastColumn, row)) {
    // more efficient to set values as [][] array than individually
    sheet.getRange(nextRowIdx, 1, 1, row.length).setValues([row]);
    lastRowIdx = nextRowIdx;
  }

  return lastRowIdx;
}

// Determines whether the new row being added matches the last row in the sheet
function isDuplicate(sheet, headers, lastRowIdx, lastColumn, row) {
  if (SCRIPT_PROP.getProperty(PROPERTY_DUPS)) {
    if (SCRIPT_PROP.getProperty(PROPERTY_DUPS) != "yes") {
      return false; // not preventing duplicates IF specified but not set to "yes"
    }
  }
  var skipHeaders = DUPS_SKIP_DEFAULT;
  if (SCRIPT_PROP.getProperty(PROPERTY_DUPS_SKIP)) {
    skipHeaders = SCRIPT_PROP.getProperty(PROPERTY_DUPS_SKIP).split(",");
  }
  var duplicate = true; // assume duplicate, prove otherwise
  var lastRowValues = sheet.getRange(lastRowIdx, 1, 1, lastColumn).getValues()[0];
  // check whether new values match previous row
  for (var i = 0; i < row.length; i++) {
    // have to ignore date fields which do not easily compare
    if (skipHeaders.indexOf(headers[i]) < 0) {
      if (row[i] != lastRowValues[i]) {
        duplicate = false;
        break;
      }
    }
  }
  // ideally, should check that all remaining fields are empty string in last row
  return duplicate;
}

function handleResponse(e) {
  // Confirm this as a valid request before doing anything
  var reqKey = SCRIPT_PROP.getProperty("api_key");
  var specifiedKey = e.parameter["API_KEY"];
  if (specifiedKey != reqKey) {
    // return json invalid credentials results
    return ContentService.createTextOutput(JSON.stringify({"result":"invalid"}))
          .setMimeType(ContentService.MimeType.JSON);
  }

  // prevent concurrent access overwritting data
  // [1] http://googleappsdeveloper.blogspot.co.uk/2011/10/concurrency-and-google-apps-script.html
  // we want a public lock, one that locks for all invocations
  var lock = LockService.getPublicLock();
  lock.waitLock(20000);  // wait 20 seconds before conceding defeat.
   
  try {
    // set where we write the data
    var doc = SpreadsheetApp.openById(SCRIPT_PROP.getProperty("key"));
    // update sheet data
    var nextRow = updateSheet(doc, e);

    // return json success results
    return ContentService
          .createTextOutput(JSON.stringify({"result":"success", "row": nextRow}))
          .setMimeType(ContentService.MimeType.JSON);
  } catch(e){
    // if error return message so that action can be taken
    return ContentService
          .createTextOutput(JSON.stringify({"result":"error", "error": e}))
          .setMimeType(ContentService.MimeType.JSON);
  } finally { //release lock
    lock.releaseLock();
  }
}

// Run once to record the unique sheet id so it can be looked up on calls
function setup() {
    var doc = SpreadsheetApp.getActiveSpreadsheet();
    SCRIPT_PROP.setProperty("key", doc.getId());
}

