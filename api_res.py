def get_api_specific_response(api_name, username=None):
    responses = { "Check Bank Balance": {"Balance": "₹ 25,450"},
                  "Get Profile": {"Name": username if username else "Unknown"},
                  "Fetch Orders": {"Orders": "3 Orders Found"},
                  "Payment Status": {"Status": "Payment Successful"},
                  "Upload File": {"Result": "File Uploaded Successfully"},
                  "Download Report": {"Report": "Report Downloaded"},
                  "Update Profile": {"Result": "Profile Updated"},
                  "Send OTP": {"OTP": "OTP Sent Successfully"},
                  "Reset Password": {"Result": "Password Reset Link Sent"},
                  "Delete Account": {"Result": "Account Deleted Successfully"}
                  }
    return responses.get(api_name, {"Message": "API Executed"}) 