Facter.add(:ipmi) do
  confine :kernel => 'Linux'
  confine :virtual => 'physical'
  setcode do
    data = Facter::Core::Execution.execute('ipmitool lan print')
    res = []
    detail = {}
    for line in data.split("\n")
      line.strip!
      if /^\s*(?<key>[^:]+):\s+(?<val>.+)$/ =~ line then
        key.downcase!.strip!.gsub!(' ', '_')
        val.strip! unless val.nil?
        if key == "ip_address" or key == "subnet_mask" then
          detail[key] = val
        elsif key == "mac_address" then
          detail["mac"] = val.gsub!(':', '')
        elsif key == "802.1q_vlan_id" then
          key = "vlan_id"
          val = nil if val == "Disabled"
          detail[key] = val
        end
      elsif line == ""
        res << detail
        detail = {}
      end
    end
    if detail then
      res << detail
    end
    res
  end
end
  