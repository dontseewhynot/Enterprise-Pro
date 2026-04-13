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
assert(validateUsername("sahil"), "validates the username field is valid")
assert(!validateUsername(""), "validates the username field is empty")
assert(!validateUsername("   "), "validates the username field is only whitespace")
assert(!validateUsername(null), "validates the username field is null")

console.log("\n--- Password Validation ---")
assert(validatePassword("abc123"), "validates the password field is at least 6 characters")
assert(validatePassword("longpassword"), "validates the password field is long enough")
assert(!validatePassword("abc"), "validates the password field is less than 6 characters")
assert(!validatePassword(""), "validates the password field is empty")
assert(!validatePassword(null), "validates the password field is null")

console.log("\n--- Form Validation ---")
assertEqual(validateUserForm("sahil", "password123"), null, "validates the user form returns null given valid form entries")
assertEqual(validateUserForm("", "password123"), "Username is required.", "validates the user form catches missing username")
assertEqual(validateUserForm("sahil", ""), "Password is required.", "validates the user form catches missing password")
assertEqual(validateUserForm("sahil", "abc"), "Password is required.", "validates the user form catches short password")

console.log("\n--- Build User List Item ---")
const user = { id: 1, username: "sahil" }
const item = buildUserListItem(user)
assert(item !== null, "builds user list item object with valid user input")
assertEqual(item.username, "sahil", "builds user list item correctly returns the username")
assertEqual(item.id, 1, "builds user list item correctly returns the id")
assert(buildUserListItem(null) === null, "builds user list item returns null for null user input")
assert(buildUserListItem({}) === null, "builds user list item returns null for user with no username")

console.log("\n--- Format User List ---")
const users = [{ id: 1, username: "sahil" }, { id: 2, username: "bob" }]
const formatted = formatUserList(users)
assertEqual(formatted.length, 2, "correctly returns the number of users in the list")
assertEqual(formatted[0].username, "sahil", "returns the correct username for the first user in the list")
assertEqual(formatUserList([]).length, 0, "returns empty array if user list is empty")
assertEqual(formatUserList(null).length, 0, "returns empty array if user list is null")
