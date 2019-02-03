Facter.add(:lldp) do
  confine :kernel => 'Linux'
  confine :virtual => 'physical'
  setcode do
    data = Facter::Core::Execution.execute('/usr/sbin/lldpcli show neighbors')
    res = {:neighbors => {}}
    interface_name, detail = nil, nil
    for line in data.split("\n")
      if line.strip == '' or line =~ /^---/ then
        res[:neighbors][interface_name] = detail if detail
        detail = nil
      elsif /^Interface:\s+(?<key>[^,]+),/ =~ line then
        interface_name, detail = key, {}
      elsif /^\s+(?<key>[^:]+): \s+(?<val>.+)$/ =~ line then
        key.downcase!.strip!
        if key == "chassis" or key == "port" or key == "unknown tlvs" or key == "tlv" then
          # ignore
        elsif key == "capability" then
          detail[key] ||= []
          if /^(?<capab>[^,]+), on/ =~ val then
            detail[key] << capab.downcase
          end
        else
          detail[key] = val.strip
        end
      end
    end
    res
  end
end
