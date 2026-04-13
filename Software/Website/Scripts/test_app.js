function assert(condition, testName) {
    if (condition) {
        console.log("PASS: " + testName)
    } else {
        console.log("FAIL: " + testName)
    }
}

function assertEqual(actual, expected, testName) {
    if (actual === expected) {
        console.log("PASS: " + testName)
    } else {
        console.log("FAIL: " + testName + " | Expected: " + expected + " | Got: " + actual)
    }
}


function validateUsername(username) {
    return username && username.trim().length > 0
}

function validatePassword(password) {
    return password && password.trim().length >= 6
}

function validateUserForm(username, password) {
    if (!validateUsername(username)) return "Username is required."
    if (!validatePassword(password)) return "Password is required."
    if (password.length < 6) return "Password must be at least 6 characters."
    return null
}

function buildUserListItem(user) {
    if (!user || !user.username) return null
    return { id: user.id, username: user.username }
}

function formatUserList(data) {
    if (!data || data.length === 0) return []
    return data.map(u => ({ id: u.id, username: u.username }))
}


console.log("--- Username Validation ---")
assert(validateUsername("sahil"), "validateUsername returns true for valid username")
assert(!validateUsername(""), "validateUsername returns false for empty string")
assert(!validateUsername("   "), "validateUsername returns false for whitespace only")
assert(!validateUsername(null), "validateUsername returns false for null")

console.log("\n--- Password Validation ---")
assert(validatePassword("abc123"), "validatePassword returns true for 6 char password")
assert(validatePassword("longpassword"), "validatePassword returns true for long password")
assert(!validatePassword("abc"), "validatePassword returns false for password under 6 chars")
assert(!validatePassword(""), "validatePassword returns false for empty password")
assert(!validatePassword(null), "validatePassword returns false for null")

console.log("\n--- Form Validation ---")
assertEqual(validateUserForm("sahil", "password123"), null, "validateUserForm returns null for valid inputs")
assertEqual(validateUserForm("", "password123"), "Username is required.", "validateUserForm catches missing username")
assertEqual(validateUserForm("sahil", ""), "Password is required.", "validateUserForm catches missing password")
assertEqual(validateUserForm("sahil", "abc"), "Password is required.", "validateUserForm catches short password")

console.log("\n--- Build User List Item ---")
const user = { id: 1, username: "sahil" }
const item = buildUserListItem(user)
assert(item !== null, "buildUserListItem returns object for valid user")
assertEqual(item.username, "sahil", "buildUserListItem returns correct username")
assertEqual(item.id, 1, "buildUserListItem returns correct id")
assert(buildUserListItem(null) === null, "buildUserListItem returns null for null input")
assert(buildUserListItem({}) === null, "buildUserListItem returns null for user with no username")

console.log("\n--- Format User List ---")
const users = [{ id: 1, username: "sahil" }, { id: 2, username: "bob" }]
const formatted = formatUserList(users)
assertEqual(formatted.length, 2, "formatUserList returns correct number of users")
assertEqual(formatted[0].username, "sahil", "formatUserList first user has correct username")
assertEqual(formatUserList([]).length, 0, "formatUserList returns empty array for empty input")
assertEqual(formatUserList(null).length, 0, "formatUserList returns empty array for null input")
