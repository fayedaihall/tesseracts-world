access(all) contract MarketplaceEscrow {
    
    access(all) event EscrowCreated(escrowId: String, buyer: Address, seller: Address, amount: UFix64)
    access(all) event EscrowFunded(escrowId: String, amount: UFix64)
    access(all) event EscrowReleased(escrowId: String, amount: UFix64)
    access(all) event EscrowDisputed(escrowId: String)
    access(all) event EscrowRefunded(escrowId: String, amount: UFix64)

    access(all) enum EscrowStatus: UInt8 {
        access(all) case Created
        access(all) case Funded
        access(all) case Released
        access(all) case Disputed
        access(all) case Refunded
    }

    access(all) struct EscrowDetails {
        access(all) let escrowId: String
        access(all) let buyer: Address
        access(all) let seller: Address
        access(all) let amount: UFix64
        access(all) let orderId: String
        access(all) var status: EscrowStatus
        access(all) let createdAt: UFix64
        access(all) var fundedAt: UFix64?
        access(all) var releasedAt: UFix64?

        init(escrowId: String, buyer: Address, seller: Address, amount: UFix64, orderId: String) {
            self.escrowId = escrowId
            self.buyer = buyer
            self.seller = seller
            self.amount = amount
            self.orderId = orderId
            self.status = EscrowStatus.Created
            self.createdAt = getCurrentBlock().timestamp
            self.fundedAt = nil
            self.releasedAt = nil
        }

        access(all) fun updateStatus(_ newStatus: EscrowStatus) {
            self.status = newStatus
        }

        access(all) fun setFunded() {
            self.fundedAt = getCurrentBlock().timestamp
            self.status = EscrowStatus.Funded
        }

        access(all) fun setReleased() {
            self.releasedAt = getCurrentBlock().timestamp
            self.status = EscrowStatus.Released
        }
    }

    access(self) let escrows: {String: EscrowDetails}
    access(self) let escrowVaults: @{String: FlowToken.Vault}

    access(all) resource Admin {
        access(all) fun resolveDispute(escrowId: String, releaseToSeller: Bool) {
            pre {
                MarketplaceEscrow.escrows.containsKey(escrowId): "Escrow does not exist"
                MarketplaceEscrow.escrows[escrowId]!.status == EscrowStatus.Disputed: "Escrow is not disputed"
            }

            let escrow = MarketplaceEscrow.escrows[escrowId]!
            let vault <- MarketplaceEscrow.escrowVaults.remove(key: escrowId)!
            
            if releaseToSeller {
                // Release to seller
                let sellerReceiver = getAccount(escrow.seller)
                    .capabilities.get<&{FungibleToken.Receiver}>(/public/flowTokenReceiver)
                    .borrow() ?? panic("Could not borrow seller receiver")
                sellerReceiver.deposit(from: <-vault)
                escrow.setReleased()
                emit EscrowReleased(escrowId: escrowId, amount: escrow.amount)
            } else {
                // Refund to buyer
                let buyerReceiver = getAccount(escrow.buyer)
                    .capabilities.get<&{FungibleToken.Receiver}>(/public/flowTokenReceiver)
                    .borrow() ?? panic("Could not borrow buyer receiver")
                buyerReceiver.deposit(from: <-vault)
                escrow.updateStatus(EscrowStatus.Refunded)
                emit EscrowRefunded(escrowId: escrowId, amount: escrow.amount)
            }

            MarketplaceEscrow.escrows[escrowId] = escrow
        }
    }

    access(all) fun createEscrow(escrowId: String, buyer: Address, seller: Address, amount: UFix64, orderId: String) {
        pre {
            !self.escrows.containsKey(escrowId): "Escrow already exists"
            amount > 0.0: "Amount must be greater than 0"
        }

        let escrow = EscrowDetails(
            escrowId: escrowId,
            buyer: buyer,
            seller: seller,
            amount: amount,
            orderId: orderId
        )

        self.escrows[escrowId] = escrow
        emit EscrowCreated(escrowId: escrowId, buyer: buyer, seller: seller, amount: amount)
    }

    access(all) fun fundEscrow(escrowId: String, payment: @FlowToken.Vault) {
        pre {
            self.escrows.containsKey(escrowId): "Escrow does not exist"
            self.escrows[escrowId]!.status == EscrowStatus.Created: "Escrow is not in Created status"
            payment.balance == self.escrows[escrowId]!.amount: "Payment amount does not match escrow amount"
        }

        let escrow = self.escrows[escrowId]!
        escrow.setFunded()
        self.escrows[escrowId] = escrow
        
        self.escrowVaults[escrowId] <-! payment
        emit EscrowFunded(escrowId: escrowId, amount: escrow.amount)
    }

    access(all) fun releaseEscrow(escrowId: String, releasedBy: Address) {
        pre {
            self.escrows.containsKey(escrowId): "Escrow does not exist"
            self.escrows[escrowId]!.status == EscrowStatus.Funded: "Escrow is not funded"
            releasedBy == self.escrows[escrowId]!.buyer || releasedBy == self.escrows[escrowId]!.seller: "Only buyer or seller can release escrow"
        }

        let escrow = self.escrows[escrowId]!
        let vault <- self.escrowVaults.remove(key: escrowId)!
        
        let sellerReceiver = getAccount(escrow.seller)
            .capabilities.get<&{FungibleToken.Receiver}>(/public/flowTokenReceiver)
            .borrow() ?? panic("Could not borrow seller receiver")
        
        sellerReceiver.deposit(from: <-vault)
        escrow.setReleased()
        self.escrows[escrowId] = escrow
        
        emit EscrowReleased(escrowId: escrowId, amount: escrow.amount)
    }

    access(all) fun disputeEscrow(escrowId: String, disputedBy: Address) {
        pre {
            self.escrows.containsKey(escrowId): "Escrow does not exist"
            self.escrows[escrowId]!.status == EscrowStatus.Funded: "Escrow is not funded"
            disputedBy == self.escrows[escrowId]!.buyer || disputedBy == self.escrows[escrowId]!.seller: "Only buyer or seller can dispute escrow"
        }

        let escrow = self.escrows[escrowId]!
        escrow.updateStatus(EscrowStatus.Disputed)
        self.escrows[escrowId] = escrow
        
        emit EscrowDisputed(escrowId: escrowId)
    }

    access(all) fun getEscrowDetails(escrowId: String): EscrowDetails? {
        return self.escrows[escrowId]
    }

    access(all) fun getEscrowsByBuyer(buyer: Address): [EscrowDetails] {
        let result: [EscrowDetails] = []
        for escrow in self.escrows.values {
            if escrow.buyer == buyer {
                result.append(escrow)
            }
        }
        return result
    }

    access(all) fun getEscrowsBySeller(seller: Address): [EscrowDetails] {
        let result: [EscrowDetails] = []
        for escrow in self.escrows.values {
            if escrow.seller == seller {
                result.append(escrow)
            }
        }
        return result
    }

    init() {
        self.escrows = {}
        self.escrowVaults <- {}

        // Create admin resource and store in account storage
        let admin <- create Admin()
        self.account.storage.save(<-admin, to: /storage/MarketplaceEscrowAdmin)
        
        // Create public capability for admin functions if needed
        self.account.capabilities.publish(
            self.account.capabilities.storage.issue<&Admin>(/storage/MarketplaceEscrowAdmin),
            at: /public/MarketplaceEscrowAdmin
        )
    }
}
