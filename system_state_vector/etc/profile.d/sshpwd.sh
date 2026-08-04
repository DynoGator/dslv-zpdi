export TEXTDOMAIN=pam_chksshpwd

if [ -e /run/sshwarn ] ; then
    echo
	echo $"SSH is enabled and the default password for the 'pi' user has not been changed."
	echo $"This is a security risk - please login as the 'pi' user and type 'passwd' to set a new password."
	echo
fi
